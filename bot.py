import telebot
from telebot import types
import random

from config import *
from db import cursor, conn

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ================== КНОПКИ ==================

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🔗 Пригласить")
    kb.add("💸 Вывод", "📜 Правила")
    kb.add("📋 Задания", "🏆 Топ")
    kb.add("🛠 Админка")
    return kb


def admin_inline():
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton("➕ ЗАДАНИЕ", callback_data="add_task"),
        types.InlineKeyboardButton("➖ ЗАДАНИЕ", callback_data="del_task")
    )
    kb.add(
        types.InlineKeyboardButton("🚫 БАН", callback_data="ban"),
        types.InlineKeyboardButton("🔍 Проверка накрута", callback_data="check_ref")
    )
    kb.add(
        types.InlineKeyboardButton("💰 Запросы на вывод", callback_data="withdraws")
    )
    return kb


# ================== START ==================

@bot.message_handler(commands=["start"])
def start(msg):
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
        (msg.from_user.id, msg.from_user.username)
    )
    conn.commit()
    bot.send_message(msg.chat.id, "✅ Добро пожаловать!", reply_markup=main_menu())


# ================== БАЛАНС ==================

@bot.message_handler(func=lambda m: "Баланс" in m.text)
def balance(msg):
    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (msg.from_user.id,)
    ).fetchone()[0]
    bot.send_message(msg.chat.id, f"💰 Ваш баланс: {bal} G")


# ================== ВЫВОД ==================

@bot.message_handler(func=lambda m: "Вывод" in m.text)
def withdraw(msg):
    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (msg.from_user.id,)
    ).fetchone()[0]

    if bal < MIN_WITHDRAW:
        bot.send_message(msg.chat.id, "❌ Минимальная сумма вывода 30G")
        return

    bot.send_message(msg.chat.id, "✍️ Введите сумму вывода:")
    bot.register_next_step_handler(msg, withdraw_amount)


def withdraw_amount(msg):
    try:
        amount = int(msg.text)
    except:
        bot.send_message(msg.chat.id, "❌ Введите число")
        return

    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (msg.from_user.id,)
    ).fetchone()[0]

    if amount < MIN_WITHDRAW or amount > bal:
        bot.send_message(msg.chat.id, "❌ Неверная сумма")
        return

    full = round(amount + random.uniform(0.01, 0.99), 2)

    cursor.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id=?",
        (amount, msg.from_user.id)
    )
    conn.commit()

    bot.send_message(
        msg.chat.id,
        f"📌 Для вывода выставьте скин за {full}G\n"
        f"📸 Отправьте скриншот скина с рынка"
    )

    bot.register_next_step_handler(msg, save_withdraw, amount, full)


def save_withdraw(msg, amount, full):
    if not msg.photo:
        bot.send_message(msg.chat.id, "❌ Нужно отправить скриншот")
        return

    file_id = msg.photo[-1].file_id

    cursor.execute(
        "INSERT INTO withdraws (user_id, amount, full_amount, photo) VALUES (?,?,?,?)",
        (msg.from_user.id, amount, full, file_id)
    )
    conn.commit()

    wid = cursor.lastrowid

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Принять", callback_data=f"wd_accept_{wid}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"wd_decline_{wid}")
    )

    bot.send_photo(
        ADMIN_ID,
        file_id,
        caption=
        f"💸 Заявка на вывод\n"
        f"👤 @{msg.from_user.username}\n"
        f"💰 Списано: {amount}G\n"
        f"📌 Выставить: {full}G",
        reply_markup=kb
    )

    bot.send_message(msg.chat.id, "⏳ Заявка отправлена администратору")


# ================== АДМИНКА ==================

@bot.message_handler(func=lambda m: "Админка" in m.text)
def admin(msg):
    if msg.from_user.id != ADMIN_ID:
        return

    bot.send_message(
        msg.chat.id,
        "🛠 Панель администратора:",
        reply_markup=admin_inline()
    )


# ================== ЗАПУСК ==================

print("BOT ONLINE")
bot.infinity_polling()

