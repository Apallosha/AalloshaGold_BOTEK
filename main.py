import telebot
from telebot import types
import random
import json
import os

TOKEN = "8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"
ADMIN_ID = 5333130126
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

def main_menu(user_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🔗 Пригласить")
    kb.add("💸 Вывод", "📜 Правила")
    kb.add("📋 Задания", "🏆 Топ")

    if int(user_id) == ADMIN_ID:
        kb.add("🛠 Админка")

    return kb

def admin_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("+ ЗАДАНИЕ", "- ЗАДАНИЕ")
    kb.add("БАН", "Проверка накрута")
    kb.add("Запросы на вывод")
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

        if " " in msg.text:
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

            if "ref" in data["users"][uid] and is_subscribed(int(uid)):
                ref = data["users"][uid]["ref"]
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
            bot.register_next_step_handler(msg, withdraw_step)

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
            text += f"{i}. ID {u[0]} - {len(u[1]['refs'])} рефов\n"
        bot.send_message(msg.chat.id, text)

    elif msg.text == "🛠 Админка" and int(uid) == ADMIN_ID:
    ikb = types.InlineKeyboardMarkup(row_width=2)

    ikb.add(
        types.InlineKeyboardButton("➕ Задание", callback_data="add_task"),
        types.InlineKeyboardButton("➖ Задание", callback_data="del_task")
    )
    ikb.add(
        types.InlineKeyboardButton("🚫 Бан", callback_data="ban"),
        types.InlineKeyboardButton("📊 Накрутка", callback_data="check_refs")
    )
    ikb.add(
        types.InlineKeyboardButton("💸 Запросы на вывод", callback_data="withdraws")
    )

    bot.send_message(
        msg.chat.id,
        "🛠 Панель администратора:",
        reply_markup=ikb
    )

    # Главное меню остаётся
    bot.send_message(
        msg.chat.id,
        "Основное меню:",
        reply_markup=main_menu()
    )


    elif msg.text == "+ ЗАДАНИЕ" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь: id, @канал, награда")
        bot.register_next_step_handler(msg, add_task)

    elif msg.text == "- ЗАДАНИЕ" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь ID задания")
        bot.register_next_step_handler(msg, del_task)

    elif msg.text == "БАН" and int(uid) == ADMIN_ID:
        bot.send_message(msg.chat.id, "Отправь ID пользователя")
        bot.register_next_step_handler(msg, ban_user)

    elif msg.text == "Проверка накрута" and int(uid) == ADMIN_ID:
        for u, info in data["users"].items():
            if len(info["refs"]) >= 7:
                bot.send_message(msg.chat.id, f"ID {u} — {len(info['refs'])} рефов")

    elif msg.text == "Запросы на вывод" and int(uid) == ADMIN_ID:
        for w in data["withdraws"]:
            bot.send_message(msg.chat.id, f"{w['user']} | {w['amount']}G")

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

def add_task(msg):
    data = load()
    try:
        tid, channel, reward = msg.text.split()
        data["tasks"][tid] = {"channel": channel, "reward": reward}
        save(data)
        bot.send_message(msg.chat.id, "Задание добавлено")
    except:
        bot.send_message(msg.chat.id, "Ошибка формата")

def del_task(msg):
    data = load()
    tid = msg.text
    if tid in data["tasks"]:
        del data["tasks"][tid]
        save(data)
        bot.send_message(msg.chat.id, "Задание удалено")

def ban_user(msg):
    data = load()
    uid = msg.text
    data["bans"].append(uid)
    save(data)
    bot.send_message(msg.chat.id, "Пользователь забанен")

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    data = load()
    uid = str(call.from_user.id)

    if int(uid) != ADMIN_ID:
        return

    if call.data == "add_task":
        bot.send_message(call.message.chat.id, "Отправь: id @канал награда")

    elif call.data == "del_task":
        bot.send_message(call.message.chat.id, "Отправь ID задания")

    elif call.data == "ban":
        bot.send_message(call.message.chat.id, "Отправь ID пользователя")

    elif call.data == "check_refs":
        for u, info in data["users"].items():
            if len(info["refs"]) >= 7:
                bot.send_message(call.message.chat.id, f"ID {u} — {len(info['refs'])} рефов")

    elif call.data == "withdraws":
        if not data["withdraws"]:
            bot.send_message(call.message.chat.id, "Нет запросов на вывод")
        else:
            for w in data["withdraws"]:
                bot.send_message(call.message.chat.id, f"{w['user']} | {w['amount']}G")

bot.poligion()
