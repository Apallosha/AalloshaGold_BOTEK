import telebot
from telebot import types
import random
import json
import os
import threading
import time
import requests
from flask import Flask

# ===== НАСТРОЙКИ =====
TOKEN = "8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"
ADMIN_ID = 5333130126
REQUIRED_CHANNELS = ["@ApalloshaTgk"]

# ===== FLASK ДЛЯ ПИНГА =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web).start()

# ===== АВТОПИНГ КАЖДЫЕ 5 МИНУТ =====
def self_ping():
    while True:
        try:
            requests.get("http://localhost:10000")
        except:
            pass
        time.sleep(300)

threading.Thread(target=self_ping).start()

# ===== TELEGRAM BOT =====
bot = telebot.TeleBot(TOKEN)
DATA_FILE = "data.json"

# ===== БАЗА =====
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "tasks": {}, "withdraws": [], "bans": []}, f)

def load():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===== ПРОВЕРКА ПОДПИСКИ =====
def is_subscribed(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

# ===== МЕНЮ =====
def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🔗 Пригласить")
    kb.add("💸 Вывод", "📜 Правила")
    kb.add("📋 Задания", "🏆 Топ")

    if int(user_id) == ADMIN_ID:
        kb.add("🛠 Админка")

    return kb

# ===== /START + КАПЧА =====
@bot.message_handler(commands=["start"])
def start(msg):
    data = load()
    uid = str(msg.from_user.id)

    if uid in data["bans"]:
        return

    if uid not in data["users"]:
        data["users"][uid] = {"balance": 0, "refs": [], "verified": False}

        if " " in msg.text:
            ref = msg.text.split()[1]
            if ref in data["users"]:
                data["users"][uid]["ref"] = ref

    a = random.randint(1, 5)
    b = random.randint(1, 5)
    data["users"][uid]["captcha"] = a + b
    save(data)

    bot.send_message(msg.chat.id, f"Реши капчу: {a} + {b}")

# ===== ОСНОВНОЙ ХЕНДЛЕР =====
@bot.message_handler(func=lambda m: True)
def handler(msg):
    data = load()
    uid = str(msg.from_user.id)

    if uid in data["bans"]:
        return

    if not data["users"][uid]["verified"]:
        if msg.text.isdigit() and int(msg.text) == data["users"][uid]["captcha"]:
            data["users"][uid]["verified"] = True

            if "ref" in data["users"][uid] and is_subscribed(int(uid)):
                ref = data["users"][uid]["ref"]
                data["users"][ref]["balance"] += 2
                data["users"][ref]["refs"].append(uid)

            save(data)
            bot.send_message(msg.chat.id, "✅ Капча пройдена", reply_markup=main_menu(uid))
        else:
            bot.send_message(msg.chat.id, "❌ Неверно")
        return

    if msg.text == "💰 Баланс":
        bot.send_message(msg.chat.id, f"Баланс: {data['users'][uid]['balance']}G")

    elif msg.text == "🔗 Пригласить":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(msg.chat.id, f"Твоя ссылка:\n{link}\n+2G за реферала")

    elif msg.text == "💸 Вывод":
        if data["users"][uid]["balance"] < 30:
            bot.send_message(msg.chat.id, "Минимальная сумма вывода 30G")
        else:
            bot.send_message(msg.chat.id, "Введи сумму вывода (от 30)")
            bot.register_next_step_handler(msg, withdraw_step)

    elif msg.text == "📜 Правила":
        bot.send_message(msg.chat.id,
            "Правила Бота:\n"
            "1. Вывод до 48 часов\n"
            "2. Обман = бан\n"
            "Удачи 🍀"
        )

    elif msg.text == "📋 Задания":
        if not data["tasks"]:
            bot.send_message(msg.chat.id, "Нет активных заданий")
        else:
            for t in data["tasks"].values():
                bot.send_message(msg.chat.id, f"Подпишись на {t['channel']} и получи {t['reward']}G")

    elif msg.text == "🏆 Топ":
        top = sorted(data["users"].items(), key=lambda x: len(x[1]["refs"]), reverse=True)[:10]
        text = "🏆 Топ рефоводов:\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. ID {u[0]} - {len(u[1]['refs'])} рефов\n"
        bot.send_message(msg.chat.id, text)

    elif msg.text == "🛠 Админка" and int(uid) == ADMIN_ID:
        ikb = types.InlineKeyboardMarkup(row_width=2)
        ikb.add(
            types.InlineKeyboardButton("➕ Задание", callback_data="add_task"),
            types.InlineKeyboardButton("➖ Задание", callback_data="del_task"),
            types.InlineKeyboardButton("🚫 Бан", callback_data="ban"),
            types.InlineKeyboardButton("📊 Накрутка", callback_data="refs"),
            types.InlineKeyboardButton("💸 Выводы", callback_data="withdraws")
        )

        bot.send_message(msg.chat.id, "🛠 Панель администратора:", reply_markup=ikb)
        bot.send_message(msg.chat.id, "Основное меню:", reply_markup=main_menu(uid))

# ===== ВЫВОД =====
def withdraw_step(msg):
    data = load()
    uid = str(msg.from_user.id)

    if not msg.text.isdigit():
        return

    amount = int(msg.text)
    if amount < 30:
        return

    data["users"][uid]["balance"] -= amount
    random_sum = round(random.uniform(amount + 0.01, amount + 0.99), 2)

    data["withdraws"].append({
        "user": f"@{msg.from_user.username}",
        "amount": random_sum
    })

    save(data)

    bot.send_message(msg.chat.id,
        f"Для вывода выставь скин за {random_sum}G\n"
        "Пришли скриншот"
    )

# ===== INLINE АДМИНКА =====
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id

    if uid != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Нет доступа", show_alert=True)
        return

    data = load()

    if call.data == "refs":
        found = False
        for u, info in data["users"].items():
            if len(info["refs"]) >= 7:
                bot.send_message(call.message.chat.id, f"ID {u} — {len(info['refs'])} рефов")
                found = True
        if not found:
            bot.send_message(call.message.chat.id, "Подозрительных нет")

    elif call.data == "withdraws":
        if not data["withdraws"]:
            bot.send_message(call.message.chat.id, "Запросов нет")
        else:
            for w in data["withdraws"]:
                bot.send_message(call.message.chat.id, f"{w['user']} | {w['amount']}G")

# ===== ЗАПУСК =====
bot.polling(none_stop=True)

