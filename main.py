# -*- coding: utf-8 -*-

import telebot
from telebot import types
import os
import sys
import io

# =======================
# UTF-8 (Railway/Linux нормально, но пусть будет)
# =======================
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# =======================
# Токен и оператор (через ENV)
# =======================
TOKEN = os.getenv("BOT_TOKEN")
OPERATOR_ID = int(os.getenv("OPERATOR_ID"))

if not TOKEN:
    raise ValueError("❌ BOT_TOKEN не задан")

bot = telebot.TeleBot(TOKEN)

ticket_counter = 0
OPERATORS = {OPERATOR_ID: "Владелец"}
active_chats = {}
ticket_messages = {}
canceled_tickets = set()
pending_tickets = {}

# =======================
# Папка логов
# =======================
os.makedirs("logs", exist_ok=True)

def log_message(ticket_id, text):
    with open(f"logs/logs{ticket_id}.txt", "a", encoding="utf-8") as f:
        f.write(text + "\n")

# =======================
# Главное меню
# =======================
def main_menu(name):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Тех. Поддержка", callback_data="support"),
        types.InlineKeyboardButton("В разработке", url="https://www.python.org"),
    )
    markup.row(
        types.InlineKeyboardButton("🌐 Discord", url="https://www.python.org"),
        types.InlineKeyboardButton("Связь с владельцем", url="https://discord.com"),
        types.InlineKeyboardButton("ℹ️ Информация", url="https://discord.gg"),
    )

    text = (
        f"Привет, {name}!\n\n"
        "Белый Аист | Поддержка\n\n"
        "Выбери действие"
    )
    return text, markup

# =======================
# /start
# =======================
@bot.message_handler(commands=["start"])
def start(message):
    text, markup = main_menu(message.from_user.first_name)
    bot.send_message(message.chat.id, text, reply_markup=markup)

# =======================
# Уведомление операторов
# =======================
def notify_operators(ticket_id, user_id, username, chat_id, message_id):
    for operator_id in OPERATORS:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "✅ Принять",
                callback_data=f"accept_{ticket_id}_{user_id}_{operator_id}_{chat_id}_{message_id}"
            ),
            types.InlineKeyboardButton(
                "🛑 Закрыть тикет",
                callback_data=f"close_ticket_{ticket_id}_{operator_id}"
            )
        )
        bot.send_message(
            operator_id,
            f"🔔 Новый тикет #{ticket_id}\nОт: @{username}",
            reply_markup=markup
        )

# =======================
# Callback
# =======================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    global ticket_counter
    username = call.from_user.username or call.from_user.first_name

    try:
        if call.data == "support":
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Підключити оператора", callback_data="connect_operator"),
                types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
            )
            bot.edit_message_text(
                f"Вітаю, {username}!\n\nНатисніть кнопку нижче.",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

        elif call.data == "connect_operator":
            ticket_counter += 1
            pending_tickets[ticket_counter] = {
                "user_id": call.from_user.id,
                "username": username,
                "chat_id": call.message.chat.id,
                "message_id": call.message.message_id
            }
            notify_operators(ticket_counter, call.from_user.id, username,
                             call.message.chat.id, call.message.message_id)

            bot.send_message(
                call.message.chat.id,
                f"Тикет #{ticket_counter} создан. Ожидание оператора."
            )

        elif call.data == "back_to_start":
            text, markup = main_menu(call.from_user.first_name)
            bot.edit_message_text(
                text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=markup
            )

    except Exception as e:
        print("Callback error:", e)

# =======================
# Пересылка сообщений
# =======================
@bot.message_handler(func=lambda m: True)
def forward_messages(message):
    if message.from_user.id in OPERATORS:
        for ticket_id, (op_id, user_id) in active_chats.items():
            if op_id == message.from_user.id:
                bot.send_message(user_id, message.text)
                return
    else:
        for ticket_id, (op_id, user_id) in active_chats.items():
            if user_id == message.from_user.id:
                bot.send_message(op_id, message.text)
                return

# =======================
# ЗАПУСК (ЭТО БЫЛО ОТСУТСТВУЮЩЕЕ)
# =======================
print("✅ Бот запущен")
bot.infinity_polling(skip_pending=True)
