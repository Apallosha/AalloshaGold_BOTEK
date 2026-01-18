import telebot
from telebot import types
import random

from config import *
from db import cursor, conn

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

# ================== НАСТРОЙКИ ==================

ADMINS = [5333130126]   # можно добавить несколько
CAPTCHA_ANSWERS = {}  # user_id: answer

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


# ================== КАПЧА ==================

def send_captcha(msg):
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    answer = a + b

    CAPTCHA_ANSWERS[msg.from_user.id] = answer

    bot.send_message(
        msg.chat.id,
        f"🤖 Подтверди, что ты не бот:\n\n{a} + {b} = ?"
    )

    bot.register_next_step_handler(msg, check_captcha)


def check_captcha(msg):
    correct = CAPTCHA_ANSWERS.get(msg.from_user.id)

    if not correct:
        return

    if not msg.text.isdigit() or int(msg.text) != correct:
        bot.send_message(msg.chat.id, "❌ Неверно. Попробуй ещё раз.")
        send_captcha(msg)
        return

    CAPTCHA_ANSWERS.pop(msg.from_user.id)

    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username) VALUES (?,?)",
        (msg.from_user.id, msg.from_user.username)
    )
    conn.commit()

    bot.send_message(msg.chat.id, "✅ Капча пройдена!", reply_markup=main_menu())


# ================== START ==================

@bot.message_handler(commands=["start"])
def start(msg):
    send_captcha(msg)


# ================== КНОПКИ ==================

@bot.message_handler(func=lambda m: "Баланс" in m.text)
def balance(msg):
    bal = cursor.execute(
        "SELECT balance FROM users WHERE user_id=?",
        (msg.from_user.id,)
    ).fetchone()[0]
    bot.send_message(msg.chat.id, f"💰 Ваш баланс: {bal} G")


@bot.message_handler(func=lambda m: "Вывод" in m.text)
def withdraw(msg):
    bot.send_message(msg.chat.id, "💸 Функция вывода в разработке")


@bot.message_handler(func=lambda m: "Задания" in m.text)
def tasks(msg):
    bot.send_message(msg.chat.id, "📋 Тут будут задания")


@bot.message_handler(func=lambda m: "Топ" in m.text)
def top(msg):
    bot.send_message(msg.chat.id, "🏆 Топ пользователей")


@bot.message_handler(func=lambda m: "Правила" in m.text)
def rules(msg):
    bot.send_message(msg.chat.id, "📜 Правила проекта")


@bot.message_handler(func=lambda m: "Пригласить" in m.text)
def invite(msg):
    bot.send_message(msg.chat.id, f"🔗 Ваша ссылка:\nhttps://t.me/{BOT_USERNAME}?start={msg.from_user.id}")


# ================== АДМИНКА ==================

@bot.message_handler(func=lambda m: "Админка" in m.text)
def admin(msg):
    if msg.from_user.id not in ADMINS:
        bot.send_message(msg.chat.id, "❌ У тебя нет доступа.")
        return

    bot.send_message(
        msg.chat.id,
        "🛠 Панель администратора:",
        reply_markup=admin_inline()
    )


# ================== CALLBACK ==================

@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    if call.from_user.id not in ADMINS:
        bot.answer_callback_query(call.id, "❌ Нет доступа")
        return

    if call.data == "add_task":
        bot.send_message(call.message.chat.id, "➕ Добавление задания")

    elif call.data == "del_task":
        bot.send_message(call.message.chat.id, "➖ Удаление задания")

    elif call.data == "ban":
        bot.send_message(call.message.chat.id, "🚫 Бан пользователя")

    elif call.data == "check_ref":
        bot.send_message(call.message.chat.id, "🔍 Проверка накрутки")

    elif call.data == "withdraws":
        bot.send_message(call.message.chat.id, "💰 Заявки на вывод")


# ================== ДЕБАГ (В САМОМ КОНЦЕ) ==================

@bot.message_handler(func=lambda m: True)
def debug(msg):
    print(repr(msg.text))


# ================== ЗАПУСК ==================

print("BOT ONLINE")
bot.infinity_polling()


