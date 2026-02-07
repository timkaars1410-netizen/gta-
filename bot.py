
#  Telegram Support Bot
#  by Magomed


import telebot
from telebot import types
import os
import sys
import io
import json
import logging
from datetime import datetime
from threading import Lock

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

TOKEN = "8597520496:AAGExrrSQCrhBazbFw3f0majl9AOwEH8Rmc"

OPERATORS = {
    7751958299: "Ростік Лютий",
}

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

class TicketManager:
    def __init__(self):
        self.counter = 0
        self.active_chats = {}
        self.ticket_messages = {}
        self.canceled_tickets = set()
        self.pending_tickets = {}
        self.lock = Lock()
        self.operators = OPERATORS
        self._ensure_directories()
        self._load_state()
    
    def _ensure_directories(self):
        for directory in ['logs', 'data']:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def _load_state(self):
        try:
            if os.path.exists('data/state.json'):
                with open('data/state.json', 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    self.counter = state.get('counter', 0)
                    logger.info(f"Стан завантажено. Лічильник тікетів: {self.counter}")
        except Exception as e:
            logger.error(f"Помилка завантаження стану: {e}")
    
    def _save_state(self):
        try:
            with open('data/state.json', 'w', encoding='utf-8') as f:
                json.dump({'counter': self.counter}, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження стану: {e}")
    
    def create_ticket(self, user_id, username, chat_id, message_id):
        with self.lock:
            self.counter += 1
            ticket_id = self.counter
            self.ticket_messages[ticket_id] = {
                'chat_id': chat_id,
                'message_id': message_id,
                'user_id': user_id,
                'username': username,
                'created_at': datetime.now().isoformat()
            }
            self.pending_tickets[ticket_id] = {
                'user_id': user_id,
                'username': username,
                'chat_id': chat_id,
                'message_id': message_id
            }
            self._save_state()
            self.log_message(ticket_id, f"Тікет створено користувачем @{username}")
            return ticket_id
    
    def accept_ticket(self, ticket_id, operator_id, user_id):
        with self.lock:
            if ticket_id in self.canceled_tickets:
                return False
            self.active_chats[ticket_id] = {
                'operator_id': operator_id,
                'user_id': user_id,
                'accepted_at': datetime.now().isoformat()
            }
            if ticket_id in self.pending_tickets:
                del self.pending_tickets[ticket_id]
            operator_name = self.operators.get(operator_id, "Оператор")
            self.log_message(ticket_id, f"Оператор {operator_name} прийняв тікет")
            return True
    
    def cancel_ticket(self, ticket_id, username):
        with self.lock:
            self.canceled_tickets.add(ticket_id)
            if ticket_id in self.pending_tickets:
                del self.pending_tickets[ticket_id]
            if ticket_id in self.active_chats:
                del self.active_chats[ticket_id]
            self.log_message(ticket_id, f"Тікет скасовано користувачем @{username}")
    
    def close_ticket(self, ticket_id):
        with self.lock:
            if ticket_id in self.active_chats:
                del self.active_chats[ticket_id]
                self.log_message(ticket_id, "Тікет закрито оператором")
                return True
            return False
    
    def get_ticket_info(self, ticket_id):
        return self.ticket_messages.get(ticket_id)
    
    def get_active_chat(self, ticket_id):
        return self.active_chats.get(ticket_id)
    
    def find_user_ticket(self, user_id):
        for ticket_id, chat_info in self.active_chats.items():
            if chat_info['user_id'] == user_id:
                return ticket_id, chat_info
        return None, None
    
    def find_operator_ticket(self, operator_id):
        for ticket_id, chat_info in self.active_chats.items():
            if chat_info['operator_id'] == operator_id:
                return ticket_id, chat_info
        return None, None
    
    def is_canceled(self, ticket_id):
        return ticket_id in self.canceled_tickets
    
    def log_message(self, ticket_id, text):
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {text}"
            with open(f"logs/ticket_{ticket_id}.txt", "a", encoding="utf-8") as f:
                f.write(log_entry + "\n")
            logger.info(f"Тікет #{ticket_id}: {text}")
        except Exception as e:
            logger.error(f"Помилка логування: {e}")

ticket_manager = TicketManager()

def safe_edit_message(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return True
    except telebot.apihelper.ApiTelegramException as e:
        if "there is no caption in the message" in str(e):
            try:
                bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode='HTML'
                )
                return True
            except Exception as e2:
                logger.error(f"Помилка редагування тексту: {e2}")
                return False
        logger.warning(f"Не вдалося редагувати повідомлення: {e}")
        return False
    except Exception as e:
        logger.error(f"Помилка редагування: {e}")
        return False

def safe_send_message(chat_id, text, reply_markup=None):
    try:
        bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode='HTML')
        return True
    except Exception as e:
        logger.error(f"Помилка відправки повідомлення: {e}")
        return False

def main_menu(name):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_support = types.InlineKeyboardButton("🧑‍💻 Зв'язок з техпідтримкою", callback_data="support")
    btn_recovery = types.InlineKeyboardButton("🔑 Відновити пароль", url="https://discord.gg/GQKt4Ez5ET")
    btn_site = types.InlineKeyboardButton("🌐 Сайт", url="https://gtaine.qniks.me/")
    btn_forum = types.InlineKeyboardButton("📔 Форум", url="https://gtaine-forum.qniks.me/index.php")
    btn_shop = types.InlineKeyboardButton("🏪 Магазин", url="https://discord.gg/GQKt4Ez5ET")
    
    markup.add(btn_support, btn_recovery)
    markup.row(btn_site, btn_forum, btn_shop)
    
    text = f"Вітаю, {name}!\n\nЯ — твій віртуальний помічник у світі GTAїна.\n\nДля початку, обери бажану дію:"
    return text, markup

@bot.message_handler(commands=['start'])
def start(message):
    try:
        name = message.from_user.first_name or "користувач"
        photo_path = "img/start.jpg"
        text, markup = main_menu(name)
        
        if os.path.exists(photo_path):
            with open(photo_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption=text, reply_markup=markup, parse_mode='HTML')
        else:
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='HTML')
        
        logger.info(f"Користувач {message.from_user.id} (@{message.from_user.username}) запустив бота")
    except Exception as e:
        logger.error(f"Помилка в start: {e}")
        safe_send_message(message.chat.id, "Сталася помилка. Спробуйте ще раз.")

def notify_operators(ticket_id, user_id, username):
    try:
        for operator_id in ticket_manager.operators.keys():
            markup = types.InlineKeyboardMarkup()
            btn_accept = types.InlineKeyboardButton(
                "✅ Прийняти",
                callback_data=f"accept_{ticket_id}"
            )
            btn_close = types.InlineKeyboardButton(
                "🛑 Закрити тікет",
                callback_data=f"close_ticket_{ticket_id}"
            )
            markup.add(btn_accept, btn_close)
            
            text = f"🔔 <b>Новий тікет #{ticket_id}</b>\n\nID: <code>{user_id}</code>\nВід: @{username}"
            safe_send_message(operator_id, text, markup)
        
        ticket_manager.log_message(ticket_id, f"Запит надіслано операторам від @{username}")
    except Exception as e:
        logger.error(f"Помилка notify_operators: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    try:
        name = call.from_user.first_name or "користувач"
        username = call.from_user.username or name
        
        if call.data == "support":
            markup = types.InlineKeyboardMarkup()
            btn_connect = types.InlineKeyboardButton("Підключити оператора", callback_data="connect_operator")
            btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
            markup.add(btn_connect, btn_back)
            text = f"Вітаю, {username}!\n\nНатисніть 'Підключити оператора' для звернення."
            safe_edit_message(call.message.chat.id, call.message.message_id, text, markup)
        
        elif call.data == "connect_operator":
            ticket_id = ticket_manager.create_ticket(
                call.from_user.id,
                username,
                call.message.chat.id,
                call.message.message_id
            )
            
            markup = types.InlineKeyboardMarkup()
            btn_cancel = types.InlineKeyboardButton(
                "❌ Скасувати. Проблема вирішена!",
                callback_data=f"cancel_ticket_{ticket_id}"
            )
            markup.add(btn_cancel)
            text = f"Вітаю, {username}!\n\n<b>Номер тікету: #{ticket_id}</b>\nСтатус: <i>Очікування оператора...</i>"
            safe_edit_message(call.message.chat.id, call.message.message_id, text, markup)
            
            notify_operators(ticket_id, call.from_user.id, username)
        
        elif call.data.startswith("cancel_ticket_"):
            ticket_id = int(call.data.split("_")[2])
            ticket_info = ticket_manager.get_ticket_info(ticket_id)
            
            if ticket_info:
                ticket_manager.cancel_ticket(ticket_id, username)
                text = f"Вітаю, {username}!\n\n<b>Номер тікету: #{ticket_id}</b>\nСтатус: Тікет скасовано."
                markup = types.InlineKeyboardMarkup()
                btn_back = types.InlineKeyboardButton("⬅️ Назад", callback_data="back_to_start")
                markup.add(btn_back)
                safe_edit_message(ticket_info['chat_id'], ticket_info['message_id'], text, markup)
                bot.answer_callback_query(call.id, text="Тікет скасовано")
        
        elif call.data.startswith("accept_"):
            ticket_id = int(call.data.split("_")[1])
            
            if ticket_manager.is_canceled(ticket_id):
                bot.answer_callback_query(call.id, text="❌ Тікет вже скасовано")
                return
            
            ticket_info = ticket_manager.get_ticket_info(ticket_id)
            if not ticket_info:
                bot.answer_callback_query(call.id, text="❌ Тікет не знайдено")
                return
            
            operator_id = call.from_user.id
            user_id = ticket_info['user_id']
            
            if ticket_manager.accept_ticket(ticket_id, operator_id, user_id):
                operator_name = ticket_manager.operators.get(operator_id, "Оператор")
                
                text = f"Вітаю, {ticket_info['username']}!\n\n<b>Номер тікету: #{ticket_id}</b>\nСтатус: Оператор {operator_name} підключився."
                safe_edit_message(ticket_info['chat_id'], ticket_info['message_id'], text, None)
                
                safe_send_message(user_id, f"✅ Оператор <b>{operator_name}</b> підключився до вашого тікету #{ticket_id}.")
                bot.answer_callback_query(call.id, text="✅ Тікет прийнято")
            else:
                bot.answer_callback_query(call.id, text="❌ Не вдалося прийняти тікет")
        
        elif call.data.startswith("close_ticket_"):
            ticket_id = int(call.data.split("_")[2])
            chat_info = ticket_manager.get_active_chat(ticket_id)
            
            if chat_info:
                user_id = chat_info['user_id']
                markup = types.InlineKeyboardMarkup(row_width=5)
                buttons = [types.InlineKeyboardButton(str(i), callback_data=f"rate_{ticket_id}_{i}") for i in range(1, 6)]
                markup.row(*buttons)
                
                safe_send_message(user_id, "Тікет закрито оператором.\n\n⭐ Оцініть роботу оператора:", markup)
                ticket_manager.close_ticket(ticket_id)
                bot.answer_callback_query(call.id, text="✅ Тікет закрито")
            else:
                bot.answer_callback_query(call.id, text="❌ Активний чат не знайдено")
        
        elif call.data.startswith("rate_"):
            parts = call.data.split("_")
            ticket_id = int(parts[1])
            rating = int(parts[2])
            
            ticket_manager.log_message(ticket_id, f"Оцінка оператора: {rating}/5")
            safe_send_message(call.from_user.id, "✅ Дякуємо за оцінку!")
            bot.answer_callback_query(call.id, text="Оцінка прийнята")
        
        elif call.data == "back_to_start":
            text, markup = main_menu(name)
            safe_edit_message(call.message.chat.id, call.message.message_id, text, markup)
    
    except Exception as e:
        logger.error(f"Помилка callback_query: {e}", exc_info=True)
        bot.answer_callback_query(call.id, text="❌ Сталася помилка")

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'video', 'document', 'audio', 'voice', 'sticker'])
def forward_messages(message):
    try:
        user_id = message.from_user.id
        
        if user_id in ticket_manager.operators:
            ticket_id, chat_info = ticket_manager.find_operator_ticket(user_id)
            if ticket_id and chat_info:
                target_user_id = chat_info['user_id']
                
                if message.content_type == 'text':
                    safe_send_message(target_user_id, f"💬 <b>Оператор:</b>\n{message.text}")
                    operator_name = ticket_manager.operators[user_id]
                    ticket_manager.log_message(ticket_id, f"Повідомлення від оператора {operator_name}: {message.text}")
                elif message.content_type == 'photo':
                    bot.send_photo(target_user_id, message.photo[-1].file_id, caption=f"💬 <b>Оператор:</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав фото")
                elif message.content_type == 'video':
                    bot.send_video(target_user_id, message.video.file_id, caption=f"💬 <b>Оператор:</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав відео")
                elif message.content_type == 'document':
                    bot.send_document(target_user_id, message.document.file_id, caption=f"💬 <b>Оператор:</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав документ")
                elif message.content_type == 'audio':
                    bot.send_audio(target_user_id, message.audio.file_id, caption=f"💬 <b>Оператор:</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав аудіо")
                elif message.content_type == 'voice':
                    bot.send_voice(target_user_id, message.voice.file_id, caption=f"💬 <b>Оператор:</b>")
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав голосове")
                elif message.content_type == 'sticker':
                    bot.send_sticker(target_user_id, message.sticker.file_id)
                    ticket_manager.log_message(ticket_id, f"Оператор надіслав стікер")
            else:
                safe_send_message(user_id, "❌ Немає активних тікетів")
        else:
            ticket_id, chat_info = ticket_manager.find_user_ticket(user_id)
            if ticket_id and chat_info:
                operator_id = chat_info['operator_id']
                
                if message.content_type == 'text':
                    safe_send_message(operator_id, f"💬 <b>Користувач (тікет #{ticket_id}):</b>\n{message.text}")
                    ticket_manager.log_message(ticket_id, f"Повідомлення від користувача: {message.text}")
                elif message.content_type == 'photo':
                    bot.send_photo(operator_id, message.photo[-1].file_id, caption=f"💬 <b>Користувач (тікет #{ticket_id}):</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав фото")
                elif message.content_type == 'video':
                    bot.send_video(operator_id, message.video.file_id, caption=f"💬 <b>Користувач (тікет #{ticket_id}):</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав відео")
                elif message.content_type == 'document':
                    bot.send_document(operator_id, message.document.file_id, caption=f"💬 <b>Користувач (тікет #{ticket_id}):</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав документ")
                elif message.content_type == 'audio':
                    bot.send_audio(operator_id, message.audio.file_id, caption=f"💬 <b>Користувач (тікет #{ticket_id}):</b>\n{message.caption or ''}")
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав аудіо")
                elif message.content_type == 'voice':
                    bot.send_voice(operator_id, message.voice.file_id, caption=f"💬 <b>Користувач (тікет #{ticket_id}):</b>")
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав голосове")
                elif message.content_type == 'sticker':
                    bot.send_sticker(operator_id, message.sticker.file_id)
                    ticket_manager.log_message(ticket_id, f"Користувач надіслав стікер")
            else:
                safe_send_message(message.chat.id, "❌ Я не розумію вас. Спробуйте /start")
    
    except Exception as e:
        logger.error(f"Помилка forward_messages: {e}", exc_info=True)

if __name__ == '__main__':
    logger.info("✅ Бот запущено")
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        logger.info("Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"Критична помилка: {e}", exc_info=True)


#  by Magomed

