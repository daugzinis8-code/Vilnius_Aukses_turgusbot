import json
import os
import time

import telebot
from telebot import types


TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("Nenurodytas TOKEN aplinkos kintamasis.")

bot = telebot.TeleBot(TOKEN)
DB = "turgus_db.json"
user_data = {}


def load_db():
    if not os.path.exists(DB):
        return []
    try:
        with open(DB, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def save_db(data):
    with open(DB, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row("🔵 PARDUODU", "🟢 PERKU")
    keyboard.row("🔍 IEŠKAU")
    keyboard.row("📋 MANO SKELBIMAI", "💰 BALANSAS")
    return keyboard


def format_listing(item):
    username = item.get("username") or ""
    return (
        f"📦 {item.get('pavadinimas', '-') }\n"
        f"💶 {item.get('kaina', '-')}\n"
        f"📍 {item.get('vieta', '-')}\n"
        f"👤 @{username}"
    )


@bot.message_handler(commands=["start"])
def start(message):
    user_data.pop(message.chat.id, None)
    bot.send_message(
        message.chat.id,
        "Vilniaus Aukštės turgus – skelbimai 24/7!",
        reply_markup=main_keyboard(),
    )


@bot.message_handler(func=lambda message: message.text == "🔵 PARDUODU")
def start_selling(message):
    user_data[message.chat.id] = {"action": "sell", "step": 1}
    bot.send_message(message.chat.id, "1/3 Ką parduodi?")


@bot.message_handler(func=lambda message: message.text == "🔍 IEŠKAU")
def start_search(message):
    user_data[message.chat.id] = {"action": "search"}
    bot.send_message(message.chat.id, "Ko ieškai?")


@bot.message_handler(func=lambda message: message.text == "🟢 PERKU")
def show_listings(message):
    listings = load_db()
    if not listings:
        bot.send_message(message.chat.id, "Turgus tuščias.", reply_markup=main_keyboard())
        return

    for item in reversed(listings[-15:]):
        bot.send_message(message.chat.id, format_listing(item))


@bot.message_handler(func=lambda message: message.text == "📋 MANO SKELBIMAI")
def show_my_listings(message):
    listings = [
        item for item in load_db() if item.get("chat_id") == message.chat.id
    ]
    if not listings:
        bot.send_message(message.chat.id, "Skelbimų neturite.")
        return

    for item in listings:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "🗑️ Ištrinti", callback_data=f"delete_{item['id']}"
            )
        )
        bot.send_message(
            message.chat.id, format_listing(item), reply_markup=keyboard
        )


@bot.message_handler(func=lambda message: message.text == "💰 BALANSAS")
def show_balance(message):
    count = sum(
        item.get("chat_id") == message.chat.id for item in load_db()
    )
    bot.send_message(message.chat.id, f"Jūsų skelbimų: {count}")


@bot.message_handler(content_types=["text"])
def handle_steps(message):
    if message.chat.id not in user_data:
        return

    data = user_data[message.chat.id]

    if data["action"] == "search":
        query = message.text.lower()
        found = [
            item
            for item in load_db()
            if query in item.get("pavadinimas", "").lower()
        ]
        if not found:
            bot.send_message(
                message.chat.id,
                f"Pagal užklausą „{message.text}“ nieko nerasta.",
                reply_markup=main_keyboard(),
            )
        else:
            for item in found:
                bot.send_message(message.chat.id, format_listing(item))
        user_data.pop(message.chat.id, None)
        return

    if data["action"] != "sell":
        return

    if data["step"] == 1:
        data["name"] = message.text
        data["step"] = 2
        bot.send_message(message.chat.id, "2/3 Kaina?")
    elif data["step"] == 2:
        data["price"] = message.text
        data["step"] = 3
        bot.send_message(message.chat.id, "3/3 Vieta Vilniuje?")
    elif data["step"] == 3:
        listings = load_db()
        listings.append(
            {
                "id": int(time.time() * 1000),
                "pavadinimas": data["name"],
                "kaina": data["price"],
                "vieta": message.text,
                "username": message.from_user.username,
                "chat_id": message.chat.id,
            }
        )
        save_db(listings)
        bot.send_message(
            message.chat.id,
            "✅ Skelbimas įdėtas!",
            reply_markup=main_keyboard(),
        )
        user_data.pop(message.chat.id, None)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_listing(call):
    listing_id = int(call.data.split("_", 1)[1])
    listings = [item for item in load_db() if item.get("id") != listing_id]
    save_db(listings)
    bot.answer_callback_query(call.id, "Skelbimas ištrintas")
    bot.edit_message_reply_markup(
        call.message.chat.id, call.message.message_id, reply_markup=None
    )


if __name__ == "__main__":
    while True:
        try:
            bot.infinity_polling(skip_pending=True)
        except Exception as error:
            print(f"Boto klaida: {error}")
            time.sleep(3)
