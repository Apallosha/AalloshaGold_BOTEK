import telebot
from telebot import types
import random
import json
import os
from datetime import datetime

TOKEN = "8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"
ADMIN_ID = 5333130126  # ТВОЙ ID

REQUIRED_CHANNELS = ["@ApalloshaTgk"]

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({"users": {}, "tasks": {}, "withdraws": [], "bans": []}, f)

def load():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def is_subscribed(user_id):
    for ch in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status not in ["member", "administrator", "creator"]:
                return False
        except:
            return False
    return True

def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🔗 Пригласить")
    kb.add("💸 Вывод", "📜 Правила")
    kb.add("📋 Задания", "🏆 Топ")
    kb.add("🛠 Админка")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    data = load()
    uid = str(msg.from_user.id)

    if uid in data["bans"]:
        return

    if uid not in data["users"]:
        data["users"][uid] = {
            "balance": 0,
            "refs": [],
            "verified": False
        }

        if msg.text.find(" ") != -1:
            ref = msg.text.split()[1]
            if ref in data["users"] and uid not in data["users"][ref]["refs"]:
                data["users"][uid]["ref"] = ref

    a = random.randint(1, 5)
    b = random.randint(1, 5)
    data["users"][uid]["captcha"] = a + b

    save(data)

    bot.send_message(msg.chat.id, f"Реши капчу: {a} + {b}")

@bot.message_handler(func=lambda m: True)
def handler(msg):
    data = load()
    uid = str(msg.from_user.id)

    if uid in data["bans"]:
        return

    if not data["users"][uid]["verified"]:
        if msg.text.isdigit() and int(msg.text) == data["users"][uid]["captcha"]:
            data["users"][uid]["verified"] = True

            if "ref" in data["users"][uid]:
                ref = data["users"][uid]["ref"]
                if is_subscribed(int(uid)):
                    data["users"][ref]["balance"] += 2
                    data["users"][ref]["refs"].append(uid)

            save(data)
            bot.send_message(msg.chat.id, "✅ Капча пройдена", reply_markup=main_menu())
        else:
            bot.send_message(msg.chat.id, "❌ Неверно")
        return

    if msg.text == "💰 Баланс":
        bot.send_message(msg.chat.id, f"Твой баланс: {data['users'][uid]['balance']}G")

    elif msg.text == "🔗 Пригласить":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(msg.chat.id, f"Приглашай друзей:\n{link}\n+2G за каждого!")

    elif msg.text == "💸 Вывод":
        bal = data["users"][uid]["balance"]
        if bal < 30:
            bot.send_message(msg.chat.id, "Минимальная сумма вывода 30G")
        else:
            bot.send_message(msg.chat.id, "Введи сумму вывода (минимум 30)")

            bot.register_next_step_handler(msg, withdraw)

    elif msg.text == "📜 Правила":
        bot.send_message(msg.chat.id,
            "Правила Бота\n"
            "1. Выводы осуществляются в ручную администратором бота, в течении 48 часов!\n"
            "2. Любой обман - блокировка аккаунта!\n"
            "Удачи 🍀"
        )

    elif msg.text == "📋 Задания":
        if not data["tasks"]:
            bot.send_message(msg.chat.id, "Нет активных заданий")
        else:
            for tid, t in data["tasks"].items():
                bot.send_message(msg.chat.id, f"Подпишись на {t['channel']} и получи {t['reward']}G")

    elif msg.text == "🏆 Топ":
        top = sorted(data["users"].items(), key=lambda x: len(x[1]["refs"]), reverse=True)[:10]
        text = "🏆 Топ рефоводов:\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. @{bot.get_chat(int(u[0])).username} - {len(u[1]['refs'])}\n"
        bot.send_message(msg.chat.id, text)

    elif msg.text == "🛠 Админка" and int(uid) == ADMIN_ID:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("+ ЗАДАНИЕ", "- ЗАДАНИЕ")
        kb.add("БАН", "Проверка накрута")
        kb.add("Запросы на вывод")
        bot.send_message(msg.chat.id, "Панель администратора:", reply_markup=kb)

    elif msg.text == "+ ЗАДАНИЕ" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь: id, @канал, награда")
        bot.register_next_step_handler(msg, add_task)

    elif msg.text == "- ЗАДАНИЕ" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь ID задания")
        bot.register_next_step_handler(msg, del_task)

    elif msg.text == "БАН" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь @username")
        bot.register_next_step_handler(msg, ban_user)

    elif msg.text == "Проверка накрута" and int(uid) == ADMIN_ID:
        for u, info in data["users"].items():
            if len(info["refs"]) >= 7:
                bot.send_message(msg.chat.id, f"@{bot.get_chat(int(u)).username} - {len(info['refs'])} рефов")

    elif msg.text == "Запросы на вывод" and int(uid) == ADMIN_ID:
        for w in data["withdraws"]:
            bot.send_message(msg.chat.id, f"{w['user']} | {w['amount']}G")

def withdraw(msg):
    data = load()
    uid = str(msg.from_user.id)

    if not msg.text.isdigit():
        return

    amount = int(msg.text)
    if amount < 30:
        return

    data["users"][uid]["balance"] -= amount

    gen = round(random.uniform(amount + 0.01, amount + 0.99), 2)

    data["withdraws"].append({
        "user": f"@{msg.from_user.username}",
        "amount": gen
    })

    save(data)

    bot.send_message(msg.chat.id,
        f"Для вывода выставь скин за {gen}G\n"
        "Пришли скриншот"
    )

bot.polling()

