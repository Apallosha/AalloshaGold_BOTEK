import os
import random
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import CommandStart
from aiogram import F

# Переменные среды
BOT_TOKEN = os.environ["8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"]
ADMIN_ID = int(os.environ["5333130126"])

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключение к базе SQLite
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Создание таблиц
cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    referrer_id INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS referrals(
    ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    ref_user_id INTEGER
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks(
    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT,
    reward REAL
)
""")
conn.commit()

# ----------------- Кнопки -----------------
def main_menu():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="Баланс", callback_data="balance"))
    kb.add(InlineKeyboardButton(text="Пригласить", callback_data="invite"))
    kb.add(InlineKeyboardButton(text="Вывод", callback_data="withdraw"))
    kb.add(InlineKeyboardButton(text="Правила", callback_data="rules"))
    kb.add(InlineKeyboardButton(text="Задания", callback_data="tasks"))
    kb.add(InlineKeyboardButton(text="Топ", callback_data="top"))
    return kb.as_markup(row_width=2)

def admin_menu():
    kb = InlineKeyboardBuilder()
    kb.add(InlineKeyboardButton(text="+ЗАДАНИЕ", callback_data="add_task"))
    kb.add(InlineKeyboardButton(text="-ЗАДАНИЕ", callback_data="del_task"))
    kb.add(InlineKeyboardButton(text="БАН", callback_data="ban_user"))
    kb.add(InlineKeyboardButton(text="Проверка накрута", callback_data="check_ref"))
    kb.add(InlineKeyboardButton(text="Запросы на вывод", callback_data="withdraw_requests"))
    return kb.as_markup(row_width=1)

# ----------------- Хендлеры -----------------
@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    # Капча
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    captcha = a + b
    await message.answer(f"Привет! Реши капчу: {a} + {b} = ?")

    # Сохраняем капчу для пользователя в памяти
    dp.current_state(user=message.from_user.id).set_data({"captcha": captcha})

@dp.message(F.text.regexp(r"^\d+$"))
async def check_captcha(message: types.Message):
    state = dp.current_state(user=message.from_user.id)
    data = await state.get_data()
    if "captcha" in data and int(message.text) == data["captcha"]:
        await message.answer("✅ Капча пройдена!", reply_markup=main_menu())
        # Добавляем пользователя в базу
        cursor.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (message.from_user.id,))
        conn.commit()
    else:
        await message.answer("❌ Неверно, попробуй ещё раз.")

# ----------------- Callback кнопок -----------------
@dp.callback_query(F.data == "balance")
async def cb_balance(call: types.CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    row = cursor.fetchone()
    balance = row[0] if row else 0
    await call.message.answer(f"Ваш баланс: {balance:.2f}G")
    await call.answer()

@dp.callback_query(F.data == "invite")
async def cb_invite(call: types.CallbackQuery):
    ref_link = f"https://t.me/YourBot?start={call.from_user.id}"
    await call.message.answer(f"Приглашай друзей по своей реферальной ссылке и получай по 2G на баланс:\n{ref_link}")
    await call.answer()

@dp.callback_query(F.data == "withdraw")
async def cb_withdraw(call: types.CallbackQuery):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (call.from_user.id,))
    balance = cursor.fetchone()[0]
    if balance < 30:
        await call.message.answer("Минимальная сумма вывода 30G")
    else:
        random_cents = random.uniform(0.01, 0.99)
        payout = balance + random_cents
        await call.message.answer(f"Приветствую! Для вывода выставьте скин за {payout:.2f}G")
        # списываем сумму, которую пользователь запросил (здесь просто весь баланс для примера)
        cursor.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (balance, call.from_user.id))
        conn.commit()
    await call.answer()

@dp.callback_query(F.data == "rules")
async def cb_rules(call: types.CallbackQuery):
    rules = (
        "Правила Бота\n"
        "1. Выводы осуществляются вручную администратором бота в течение 48 часов!\n"
        "2. Любой обман с вашей стороны - блокировка аккаунта!\n"
        "Не нарушайте правила, удачи 🍀"
    )
    await call.message.answer(rules)
    await call.answer()

# ----------------- Админка -----------------
@dp.callback_query(F.data == "admin")
async def cb_admin(call: types.CallbackQuery):
    if call.from_user.id == ADMIN_ID:
        await call.message.answer("Панель администратора:", reply_markup=admin_menu())
    await call.answer()

# ----------------- Запуск -----------------
if __name__ == "__main__":
    import asyncio
    asyncio.run(dp.start_polling(bot))

