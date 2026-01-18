import os 
import asyncio
import random
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage

# ================= НАСТРОЙКИ =================
BOT_TOKEN = os.environ["8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"]
ADMIN_ID = int(os.environ[5333130126])
REWARD_PER_REF = 2
MIN_WITHDRAW = 30

REQUIRED_CHANNELS = [
    "@example_channel1",
    "@example_channel2"
]
# =============================================

bot = Bot(BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect("database.db")
sql = db.cursor()

# ================= БАЗА =================
sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance INTEGER DEFAULT 0,
    referrer INTEGER,
    referrals INTEGER DEFAULT 0,
    captcha INTEGER DEFAULT 0,
    banned INTEGER DEFAULT 0
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY,
    channel TEXT,
    reward INTEGER
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    generated REAL,
    status TEXT
)
""")
db.commit()

# ================= FSM =================
class Captcha(StatesGroup):
    wait = State()

class Withdraw(StatesGroup):
    amount = State()
    screenshot = State()

class AddTask(StatesGroup):
    data = State()

class RemoveTask(StatesGroup):
    id = State()

class BanUser(StatesGroup):
    username = State()

# ================= КЛАВИАТУРЫ =================
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🔗 Пригласить")],
        [KeyboardButton(text="💸 Вывод")],
        [KeyboardButton(text="📋 Задания"), KeyboardButton(text="🏆 Топ")],
        [KeyboardButton(text="📜 Правила")]
    ],
    resize_keyboard=True
)

admin_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="+ЗАДАНИЕ"), KeyboardButton(text="-ЗАДАНИЕ")],
        [KeyboardButton(text="БАН"), KeyboardButton(text="Проверка накрута")],
        [KeyboardButton(text="Запросы на вывод")]
    ],
    resize_keyboard=True
)

# ================= /START + КАПЧА =================
@dp.message(F.text.startswith("/start"))
async def start(message: Message, state: FSMContext):
    sql.execute("SELECT banned FROM users WHERE user_id=?", (message.from_user.id,))
    ban = sql.fetchone()
    if ban and ban[0] == 1:
        return

    ref = None
    if len(message.text.split()) > 1:
        ref = int(message.text.split()[1])

    sql.execute("INSERT OR IGNORE INTO users (user_id, username, referrer) VALUES (?,?,?)",
                (message.from_user.id, message.from_user.username, ref))
    db.commit()

    a, b = random.randint(1, 9), random.randint(1, 9)
    await state.set_state(Captcha.wait)
    await state.update_data(ans=a + b)
    await message.answer(f"🤖 Подтвердите, что вы не бот:\n\n{a} + {b} = ?")

@dp.message(Captcha.wait)
async def captcha_check(message: Message, state: FSMContext):
    data = await state.get_data()
    if not message.text.isdigit() or int(message.text) != data["ans"]:
        return await message.answer("❌ Неверно, попробуйте ещё раз")

    sql.execute("UPDATE users SET captcha=1 WHERE user_id=?", (message.from_user.id,))
    db.commit()

    await state.clear()
    await message.answer("✅ Добро пожаловать!", reply_markup=menu)

# ================= БАЛАНС =================
@dp.message(F.text == "💰 Баланс")
async def balance(message: Message):
    sql.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    bal = sql.fetchone()[0]
    await message.answer(f"💰 Ваш баланс: {bal} G")

# ================= ПРИГЛАСИТЬ =================
@dp.message(F.text == "🔗 Пригласить")
async def invite(message: Message):
    link = f"https://t.me/{(await bot.me()).username}?start={message.from_user.id}"
    await message.answer(
        "Приглашай друзей по своей реферальной ссылке и получай по 2G на баланс\n\n"
        f"{link}"
    )

# ================= ВЫВОД =================
@dp.message(F.text == "💸 Вывод")
async def withdraw(message: Message, state: FSMContext):
    sql.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
    bal = sql.fetchone()[0]

    if bal < MIN_WITHDRAW:
        return await message.answer("Минимальная сумма вывода 30G")

    await state.set_state(Withdraw.amount)
    await message.answer("Введите сумму вывода (минимум 30G):")

@dp.message(Withdraw.amount)
async def withdraw_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        return await message.answer("Введите число")

    amount = int(message.text)
    if amount < MIN_WITHDRAW:
        return await message.answer("Минимум 30G")

    rnd = round(amount + random.uniform(0.01, 0.99), 2)

    sql.execute("UPDATE users SET balance = balance - ? WHERE user_id=?",
                (amount, message.from_user.id))
    sql.execute("INSERT INTO withdrawals (user_id, amount, generated, status) VALUES (?,?,?,?)",
                (message.from_user.id, amount, rnd, "wait"))
    db.commit()

    await state.update_data(gen=rnd)
    await state.set_state(Withdraw.screenshot)

    await message.answer(
        "Приветствую! Для вывода G в игру Standoff2 тебе нужно:\n"
        "1. Купить любой скин с патерном\n"
        "2. Выставить его за сумму ниже\n\n"
        f"💰 Для вывода выставьте скин за {rnd}G\n\n"
        "Отправьте скриншот"
    )

@dp.message(Withdraw.screenshot)
async def withdraw_screen(message: Message, state: FSMContext):
    if not message.photo:
        return await message.answer("Отправьте скриншот")

    data = await state.get_data()
    await bot.send_photo(
        ADMIN_ID,
        message.photo[-1].file_id,
        caption=f"💸 Заявка на вывод\n"
                f"👤 @{message.from_user.username}\n"
                f"💰 Сумма: {data['gen']}G"
    )

    await state.clear()
    await message.answer("⏳ Заявка отправлена администратору")

# ================= ПРАВИЛА =================
@dp.message(F.text == "📜 Правила")
async def rules(message: Message):
    await message.answer(
        "Правила Бота\n"
        "1. Выводы осуществляются вручную администратором в течении 48 часов\n"
        "2. Любой обман — блокировка аккаунта\n\n"
        "Удачи 🍀"
    )

# ================= ТОП =================
@dp.message(F.text == "🏆 Топ")
async def top(message: Message):
    sql.execute("SELECT username, referrals FROM users ORDER BY referrals DESC LIMIT 10")
    rows = sql.fetchall()
    text = "🏆 Топ рефоводов:\n\n"
    for i, r in enumerate(rows, 1):
        text += f"{i}. @{r[0]} — {r[1]}\n"
    await message.answer(text)

# ================= АДМИНКА =================
@dp.message(F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message):
    if message.text == "Админка":
        await message.answer("Панель администратора:", reply_markup=admin_kb)

# ================= ЗАПУСК =================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

