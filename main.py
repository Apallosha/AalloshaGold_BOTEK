import telebot
from telebot import types
import random, json, os, threading, time, requests
from flask import Flask

# ================= НАСТРОЙКИ =================
TOKEN = "8537615630:AAHv_JKJEml7qxuGxI9wbCSUFTg9N5uBDL0"
ADMIN_ID = 5333130126
REQUIRED_CHANNELS = ["@ApalloshaTgk"]  # обязательные каналы
DATA_FILE = "data.json"

# ================= FLASK (PING) =================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive"

def run_web():
    app.run(host="0.0.0.0", port=10000)

threading.Thread(target=run_web, daemon=True).start()

def self_ping():
    while True:
        try:
            requests.get("http://localhost:10000")
        except:
            pass
        time.sleep(300)

threading.Thread(target=self_ping, daemon=True).start()

# ================= BOT =================
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= DATA =================
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump(
            {"users": {}, "tasks": {}, "withdraws": [], "bans": []},
            f
        )

def load():
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ================= HELPERS =================
def is_subscribed(uid):
    for ch in REQUIRED_CHANNELS:
        try:
            st = bot.get_chat_member(ch, uid).status
            if st not in ("member", "administrator", "creator"):
                return False
        except:
            return False
    return True

def main_menu(uid):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Баланс", "🔗 Пригласить")
    kb.add("💸 Вывод", "📜 Правила")
    kb.add("📋 Задания", "🏆 Топ")
    if uid == ADMIN_ID:
        kb.add("🛠 Админка")
    return kb

# ================= START + CAPTCHA =================
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

        if len(msg.text.split()) > 1:
            ref = msg.text.split()[1]
            if ref in data["users"] and ref != uid:
                data["users"][uid]["ref"] = ref

    a, b = random.randint(1, 5), random.randint(1, 5)
    data["users"][uid]["captcha"] = a + b
    save(data)

    bot.send_message(msg.chat.id, f"Реши капчу: {a} + {b}")

# ================= ADMIN STATES =================
admin_states = {}

# ================= MAIN HANDLER =================
@bot.message_handler(func=lambda m: True)
def handler(msg):
    data = load()
    uid = str(msg.from_user.id)

    if uid in data["bans"]:
        return

    # ---- ADMIN INPUT ----
    if msg.from_user.id in admin_states:
        state = admin_states.pop(msg.from_user.id)

        if state == "add_task":
            try:
                tid, channel, reward = msg.text.split()
                data["tasks"][tid] = {
                    "channel": channel,
                    "reward": int(reward)
                }
                save(data)
                bot.send_message(msg.chat.id, "✅ Задание добавлено")
            except:
                bot.send_message(msg.chat.id, "❌ Формат: id @канал награда")
            return

        if state == "del_task":
            tid = msg.text
            if tid in data["tasks"]:
                del data["tasks"][tid]
                save(data)
                bot.send_message(msg.chat.id, "🗑 Задание удалено")
            else:
                bot.send_message(msg.chat.id, "❌ Не найдено")
            return

        if state == "ban":
            data["bans"].append(msg.text)
            save(data)
            bot.send_message(msg.chat.id, "🚫 Пользователь забанен")
            return

    # ---- CAPTCHA ----
    if not data["users"][uid]["verified"]:
        if msg.text.isdigit() and int(msg.text) == data["users"][uid]["captcha"]:
            data["users"][uid]["verified"] = True

            if "ref" in data["users"][uid] and is_subscribed(int(uid)):
                ref = data["users"][uid]["ref"]
                data["users"][ref]["balance"] += 2
                data["users"][ref]["refs"].append(uid)

            save(data)
            bot.send_message(msg.chat.id, "✅ Капча пройдена", reply_markup=main_menu(msg.from_user.id))
        else:
            bot.send_message(msg.chat.id, "❌ Неверно")
        return

    # ---- BUTTONS ----
    if msg.text == "💰 Баланс":
        bot.send_message(msg.chat.id, f"Ваш баланс: {data['users'][uid]['balance']}G")

    elif msg.text == "🔗 Пригласить":
        link = f"https://t.me/{bot.get_me().username}?start={uid}"
        bot.send_message(
            msg.chat.id,
            f"Приглашай друзей по своей реферальной ссылке и получай по 2G за одного друга!\n\n{link}"
        )

    elif msg.text == "📜 Правила":
        bot.send_message(
            msg.chat.id,
            "📜 <b>Правила Бота</b>\n\n"
            "Выводы осуществляются в ручную, в течении 48 часов!\n"
            "За любой обман/накрутку ваш аккаунт будет заблокирован!\n\n"
            "Удачи ☘️"
        )

    elif msg.text == "📋 Задания":
        if not data["tasks"]:
            bot.send_message(msg.chat.id, "Нет активных заданий")
        else:
            for tid, t in data["tasks"].items():
                ikb = types.InlineKeyboardMarkup()
                ikb.add(
                    types.InlineKeyboardButton(
                        "✅ Проверить задание",
                        callback_data=f"check_{tid}"
                    )
                )
                bot.send_message(
                    msg.chat.id,
                    f"<b>Задание {tid}!</b>\n"
                    f"Подпишись на {t['channel']} и получи {t['reward']}G",
                    reply_markup=ikb
                )

    elif msg.text == "🏆 Топ":
        top = sorted(
            data["users"].items(),
            key=lambda x: len(x[1]["refs"]),
            reverse=True
        )[:10]

        text = "🏆 <b>Топ рефоводов</b>\n\n"
        for i, u in enumerate(top, 1):
            text += f"{i}. ID {u[0]} — {len(u[1]['refs'])}\n"

        bot.send_message(msg.chat.id, text)

    elif msg.text == "🛠 Админка" and msg.from_user.id == ADMIN_ID:
        ikb = types.InlineKeyboardMarkup(row_width=2)
        ikb.add(
            types.InlineKeyboardButton("➕ Задание", callback_data="add_task"),
            types.InlineKeyboardButton("➖ Задание", callback_data="del_task"),
            types.InlineKeyboardButton("🚫 Бан", callback_data="ban")
        )
        bot.send_message(msg.chat.id, "🛠 <b>Панель администратора</b>", reply_markup=ikb)

# ================= CALLBACKS =================
@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    data = load()
    uid = str(call.from_user.id)

    # ---- ADMIN ----
    if call.data in ("add_task", "del_task", "ban"):
        if call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ Нет доступа", show_alert=True)
            return

        admin_states[call.from_user.id] = call.data
        texts = {
            "add_task": "Отправь: id @канал награда",
            "del_task": "Отправь ID задания",
            "ban": "Отправь ID пользователя"
        }
        bot.send_message(call.message.chat.id, texts[call.data])
        return

    # ---- CHECK TASK ----
    if call.data.startswith("check_"):
        tid = call.data.split("_")[1]

        if tid not in data["tasks"]:
            bot.answer_callback_query(call.id, "❌ Задание не найдено", show_alert=True)
            return

        task = data["tasks"][tid]

        try:
            st = bot.get_chat_member(task["channel"], call.from_user.id).status
            if st in ("member", "administrator", "creator"):
                data["users"][uid]["balance"] += task["reward"]
                del data["tasks"][tid]
                save(data)
                bot.edit_message_text(
                    f"✅ Задание выполнено! +{task['reward']}G",
                    call.message.chat.id,
                    call.message.message_id
                )
            else:
                bot.answer_callback_query(call.id, "❌ Ты не подписан", show_alert=True)
        except:
            bot.answer_callback_query(call.id, "❌ Ошибка проверки", show_alert=True)

# ================= RUN =================
bot.polling(none_stop=True)

