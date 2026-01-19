import telebot
from telebot import types
from flask import Flask
import json
import os
import random

TOKEN = "8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"
ADMIN_ID = 5333130126
BOT_USERNAME = "@ApalloshaGold_Bot"
REQUIRED_CHANNELS = ["@ApalloshaTgk"]

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

DATA_FILE = "data.json"

def load():
    if not os.path.exists(DATA_FILE):
        return {"users": {}, "tasks": {}, "withdraws": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load()

@app.route("/")
def home():
    return "Bot is alive"

def is_subscribed(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ["left", "kicked"]:
                return False
        except:
            return False
    return True

def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "👥 Пригласить")
    kb.add("💸 Вывод", "📋 Задания")
    kb.add("📊 Топ", "📜 Правила")
    if uid == ADMIN_ID:
        kb.add("🛠 Админка")
    return kb

@bot.message_handler(commands=["start"])
def start(msg):
    uid = str(msg.from_user.id)

    if not is_subscribed(msg.from_user.id):
        kb = types.InlineKeyboardMarkup()
        for ch in REQUIRED_CHANNELS:
            kb.add(types.InlineKeyboardButton(ch, url=f"https://t.me/{ch[1:]}"))
        kb.add(types.InlineKeyboardButton("Проверить подписку", callback_data="check_sub"))

        bot.send_message(msg.chat.id, "Подпишись на канал, чтобы пользоваться ботом:", reply_markup=kb)
        return

    if uid not in data["users"]:
        a, b = random.randint(1, 9), random.randint(1, 9)
        data["users"][uid] = {
            "balance": 0,
            "captcha": a + b,
            "refs": 0,
            "verified": False
        }
        save(data)
        bot.send_message(msg.chat.id, f"Капча: {a} + {b} = ?")
    else:
        bot.send_message(msg.chat.id, "Главное меню", reply_markup=main_menu(msg.from_user.id))

@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub(call):
    if is_subscribed(call.from_user.id):
        bot.send_message(call.message.chat.id, "✅ Подписка подтверждена. Нажми /start")
    else:
        bot.answer_callback_query(call.id, "❌ Ты не подписался", show_alert=True)

@bot.message_handler(func=lambda m: str(m.from_user.id) in data["users"] and not data["users"][str(m.from_user.id)]["verified"])
def captcha_check(msg):
    uid = str(msg.from_user.id)
    if msg.text.isdigit() and int(msg.text) == data["users"][uid]["captcha"]:
        data["users"][uid]["verified"] = True
        save(data)
        bot.send_message(msg.chat.id, "✅ Капча пройдена", reply_markup=main_menu(msg.from_user.id))
    else:
        bot.send_message(msg.chat.id, "❌ Неверно")

@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(msg):
    uid = str(msg.from_user.id)
    bot.send_message(msg.chat.id, f"Ваш баланс: {data['users'][uid]['balance']}G")

@bot.message_handler(func=lambda m: m.text == "👥 Пригласить")
def invite(msg):
    uid = msg.from_user.id
    link = f"https://t.me/{BOT_USERNAME}?start={uid}"
    bot.send_message(
        msg.chat.id,
        f"Приглашай друзей по своей реферальной ссылке и получай по 2G за одного друга!\n\n{link}"
    )

@bot.message_handler(func=lambda m: m.text == "💸 Вывод")
def withdraw(msg):
    uid = str(msg.from_user.id)
    bal = data["users"][uid]["balance"]
    if bal < 30:
        bot.send_message(msg.chat.id, "Минимальная сумма вывода 30G")
    else:
        bot.send_message(msg.chat.id, "Введите сумму вывода (от 30G)")
        bot.register_next_step_handler(msg, withdraw_amount)

def withdraw_amount(msg):
    uid = str(msg.from_user.id)
    if not msg.text.isdigit():
        bot.send_message(msg.chat.id, "Введите число")
        return

    amount = int(msg.text)
    if amount < 30 or amount > data["users"][uid]["balance"]:
        bot.send_message(msg.chat.id, "❌ Неверная сумма")
        return

    final_sum = round(random.uniform(amount + 0.01, amount + 0.99), 2)
    data["users"][uid]["balance"] -= amount

    wid = len(data["withdraws"])
    data["withdraws"].append({
        "id": wid,
        "uid": uid,
        "user": f"@{msg.from_user.username}",
        "amount": final_sum,
        "status": "pending"
    })
    save(data)

    bot.send_message(
        msg.chat.id,
        f"Для вывода выставьте скин за <b>{final_sum}G</b>\n"
        "После этого отправьте скриншот."
    )
    bot.register_next_step_handler(msg, withdraw_photo)

def withdraw_photo(msg):
    if not msg.photo:
        bot.send_message(msg.chat.id, "❌ Отправьте скриншот")
        return

    w = data["withdraws"][-1]

    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_{w['id']}"),
        types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_{w['id']}")
    )

    bot.send_photo(
        ADMIN_ID,
        msg.photo[-1].file_id,
        caption=f"💸 Запрос на вывод\n\n👤 {w['user']}\n💰 {w['amount']}G",
        reply_markup=kb
    )

    bot.send_message(msg.chat.id, "⏳ Запрос отправлен администратору")

@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id == ADMIN_ID)
def admin(msg):
    kb = types.InlineKeyboardMarkup()
    bot.send_message(msg.chat.id, "🛠 Панель администратора", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.from_user.id == ADMIN_ID)
def admin_callbacks(call):
    if call.data.startswith("accept_"):
        wid = int(call.data.split("_")[1])
        data["withdraws"][wid]["status"] = "accepted"
        save(data)
        bot.answer_callback_query(call.id, "✅ Принято")
        bot.send_message(int(data["withdraws"][wid]["uid"]), "✅ Ваш вывод принят")

    if call.data.startswith("decline_"):
        wid = int(call.data.split("_")[1])
        data["withdraws"][wid]["status"] = "declined"
        save(data)
        bot.answer_callback_query(call.id, "❌ Отклонено")
        bot.send_message(int(data["withdraws"][wid]["uid"]), "❌ Ваш вывод отклонён")

@bot.message_handler(func=lambda m: m.text == "📜 Правила")
def rules(msg):
    bot.send_message(
        msg.chat.id,
        "Правила Бота\n\n"
        "Выводы осуществляются в ручную, в течении 48 часов!\n"
        "За любой обман/накрутку ваш аккаунт будет заблокирован!\n"
        "Удачи ☘️"
    )

bot.polling(none_stop=True)

