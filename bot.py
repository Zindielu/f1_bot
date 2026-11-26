import telebot
import time
import threading
import sqlite3
import pytz
import traceback
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==========================================
# НАСТРОЙКИ
# ==========================================
BOT_TOKEN = "9023464869:AAG7tjtHT0msE1bvkb_U00ucfOvfGJgSuak"
ADMIN_ID = 7102362294 

# ==========================================
# ВРЕМЯ ПО МСК
# ==========================================
MSK = pytz.timezone('Europe/Moscow')
def get_now():
    return datetime.now(MSK)

# ==========================================
# БАЗА ДАННЫХ (с защитой)
# ==========================================
def init_db():
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                          (chat_id INTEGER PRIMARY KEY, is_subscribed INTEGER)''')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Init Error: {e}")

def add_user(chat_id):
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (chat_id, is_subscribed) VALUES (?, 0)", (chat_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Add Error: {e}")

def set_subscription(chat_id, status):
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET is_subscribed = ? WHERE chat_id = ?", (status, chat_id))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Sub Error: {e}")

def get_all_users():
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users")
        users = [row[0] for row in cursor.fetchall()]
        conn.close()
        return users
    except:
        return []

def get_subscribers():
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT chat_id FROM users WHERE is_subscribed = 1")
        subs = [row[0] for row in cursor.fetchall()]
        conn.close()
        return subs
    except:
        return []

# ==========================================
# РАСПИСАНИЕ
# ==========================================
WEEKENDS = {
    "🇶🇦 Гран-при Катара (27-29 ноя)": [
        (MSK.localize(datetime(2026, 11, 27, 16, 30)), "Практика 1"),
        (MSK.localize(datetime(2026, 11, 27, 20, 0)), "Практика 2"),
        (MSK.localize(datetime(2026, 11, 28, 17, 30)), "Практика 3"),
        (MSK.localize(datetime(2026, 11, 28, 21, 0)), "Квалификация"),
        (MSK.localize(datetime(2026, 11, 29, 19, 0)), "🏁 ГОНКА")
    ],
    "🇦🇪 Гран-при Абу-Даби (4-6 дек)": [
        (MSK.localize(datetime(2026, 12, 4, 12, 30)), "Практика 1"),
        (MSK.localize(datetime(2026, 12, 4, 16, 0)), "Практика 2"),
        (MSK.localize(datetime(2026, 12, 5, 13, 30)), "Практика 3"),
        (MSK.localize(datetime(2026, 12, 5, 17, 0)), "Квалификация"),
        (MSK.localize(datetime(2026, 12, 6, 16, 0)), "🏁 ГОНКА")
    ]
}

# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def get_start_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚀 Поехали!", callback_data="go"))
    return markup

def get_main_keyboard(chat_id):
    try:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🏁 Ближайшая гонка", callback_data="next"))
        markup.add(InlineKeyboardButton("📅 Все гонки", callback_data="racedate"))
        
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute("SELECT is_subscribed FROM users WHERE chat_id = ?", (chat_id,))
        res = cursor.fetchone()
        conn.close()
        
        is_sub = res[0] if res else 0
        
        if is_sub == 0:
            markup.add(InlineKeyboardButton("🔔 Подписаться", callback_data="subscribe"))
        else:
            markup.add(InlineKeyboardButton("📩 Сообщить о проблеме", callback_data="feedback"))
            markup.add(InlineKeyboardButton("🔕 Отписаться", callback_data="unsubscribe"))
        return markup
    except:
        return InlineKeyboardMarkup()

def get_weekend_keyboard():
    markup = InlineKeyboardMarkup()
    for i, name in enumerate(WEEKENDS.keys(), 1):
        markup.add(InlineKeyboardButton(name, callback_data=f"weekend_{i}"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return markup

def get_feedback_admin_keyboard(user_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🚫 Забанить", callback_data=f"ban_{user_id}"))
    markup.add(InlineKeyboardButton("💬 Ответить", callback_data=f"reply_{user_id}"))
    return markup

# ==========================================
# ИНИЦИАЛИЗАЦИЯ
# ==========================================
try:
    bot = telebot.TeleBot(BOT_TOKEN)
    init_db()
    print("Бот запущен и ждет сообщений...")
except Exception as e:
    print(f"Ошибка при запуске: {e}")

reply_mode = {}

# ==========================================
# ОБРАБОТЧИКИ (С ЗАЩИТОЙ)
# ==========================================
@bot.message_handler(commands=['start'])
def start_message(message):
    try:
        add_user(message.chat.id)
        bot.send_message(message.chat.id, 
            "Привет! Я бот-напоминалка Ф1. 🏎️\n\n"
            "Все времена указаны по МСК.\nНажми на кнопку ниже, чтобы начать!",
            reply_markup=get_start_keyboard())
    except Exception as e:
        print(f"Start Error: {e}")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        chat_id = call.message.chat.id
        bot.answer_callback_query(call.id)
        
        if call.data == "go":
            bot.edit_message_text("Отлично! Выбери действие:", chat_id, call.message.message_id, reply_markup=get_main_keyboard(chat_id))
        
        elif call.data == "next":
            all_events = []
            for weekend in WEEKENDS.values():
                all_events.extend(weekend)
            
            now = get_now()
            upcoming = [e for e in all_events if e[0] > now]
            
            if not upcoming:
                text = "Пока нет будущих событий."
            else:
                upcoming.sort(key=lambda x: x[0])
                next_date, next_name = upcoming[0]
                delta = next_date - now
                days, hours, minutes = delta.days, delta.seconds // 3600, (delta.seconds % 3600) // 60
                text = f"🏁 Ближайшее событие: *{next_name}*\n📅 Старт: {next_date.strftime('%d.%m в %H:%M')} (МСК)\n⏳ Осталось: {days} д. {hours} ч. {minutes} мин."
            
            bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=get_main_keyboard(chat_id))

        elif call.data == "racedate":
            bot.send_message(chat_id, "📅 Выбери уикенд:", reply_markup=get_weekend_keyboard())

        elif call.data.startswith("weekend_"):
            index = int(call.data.split("_")[1]) - 1
            weekend_name = list(WEEKENDS.keys())[index]
            text = f"📅 *Расписание: {weekend_name}* (МСК)\n\n"
            for race_time, race_name in WEEKENDS[weekend_name]:
                text += f"• {race_time.strftime('%d.%m в %H:%M')} — {race_name}\n"
            bot.send_message(chat_id, text, parse_mode='Markdown', reply_markup=get_main_keyboard(chat_id))

        elif call.data == "subscribe":
            set_subscription(chat_id, 1)
            bot.send_message(chat_id, "✅ Поздравляю, ты подписан! Я пришлю напоминания за час, за 10 минут и в момент старта.\n\n"
                                      "💡 Если захочешь отписаться, просто нажми «Отписаться».", 
                             reply_markup=get_main_keyboard(chat_id))

        elif call.data == "unsubscribe":
            set_subscription(chat_id, 0)
            bot.send_message(chat_id, "❌ Ты отписан. Больше не буду присылать уведомления.", 
                             reply_markup=get_main_keyboard(chat_id))

        elif call.data == "feedback":
            bot.send_message(chat_id, "📝 Напиши свою жалобу или идею.")

        elif call.data == "back":
            bot.edit_message_text("Главное меню:", chat_id, call.message.message_id, reply_markup=get_main_keyboard(chat_id))

        elif call.data.startswith("ban_"):
            user_id = int(call.data.split("_")[1])
            bot.send_message(user_id, "🚫 Твоя жалоба отклонена. Выдан мут на 24 часа за нарушение правил.")
            bot.edit_message_text("🚫 Пользователь забанен на 24 часа.", chat_id, call.message.message_id)

        elif call.data.startswith("reply_"):
            user_id = int(call.data.split("_")[1])
            reply_mode[chat_id] = user_id
            bot.send_message(chat_id, "💬 Напиши текст ответа для пользователя:")

    except Exception as e:
        print(f"Callback Error: {e}")
        # Не даем боту упасть, просто сообщаем пользователю
        try:
            bot.send_message(call.message.chat.id, "Произошла небольшая ошибка. Попробуй еще раз.", reply_markup=get_main_keyboard(call.message.chat.id))
        except:
            pass

@bot.message_handler(commands=['stats'])
def stats(message):
    try:
        if message.chat.id != ADMIN_ID:
            bot.send_message(message.chat.id, "У тебя нет прав на эту команду.")
            return
        all_u = get_all_users()
        subs = get_subscribers()
        bot.send_message(ADMIN_ID, f"📊 Всего пользователей: {len(all_u)}\n🔔 Подписчиков: {len(subs)}")
    except Exception as e:
        print(f"Stats Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        if message.chat.id == ADMIN_ID and message.chat.id in reply_mode:
            user_id = reply_mode[message.chat.id]
            bot.send_message(user_id, f"💬 *Ответ разработчика:*\n\n{message.text}", parse_mode='Markdown')
            bot.send_message(ADMIN_ID, "✅ Ответ отправлен пользователю.")
            del reply_mode[message.chat.id]
            return

        if message.text.startswith('/'):
            bot.send_message(message.chat.id, "Я не знаю такой команды. Используй кнопки ниже.", reply_markup=get_main_keyboard(message.chat.id))
        else:
            bot.send_message(ADMIN_ID, 
                             f"📩 Жалоба от {message.from_user.username} (ID: {message.chat.id}):\n\n{message.text}",
                             reply_markup=get_feedback_admin_keyboard(message.chat.id))
            bot.send_message(message.chat.id, "✅ Спасибо! Твоя жалоба передана разработчику.", reply_markup=get_main_keyboard(message.chat.id))
    except Exception as e:
        print(f"Message Error: {e}")

# ==========================================
# НАПОМИНАНИЯ
# ==========================================
def reminder_worker():
    sent_reminders = set()
    while True:
        try:
            now = get_now()
            subs = get_subscribers()
            
            for weekend_name, events in WEEKENDS.items():
                for event_time, event_name in events:
                    delta = event_time - now
                    minutes_left = delta.total_seconds() / 60
                    
                    if subs:
                        if 59.5 < minutes_left <= 60.5 and f"{event_name}_1h" not in sent_reminders:
                            for user in subs:
                                try: bot.send_message(user, f"⏰ *Напоминание за час!*\nДо старта '{event_name}' остался 1 час (МСК).")
                                except: pass
                            sent_reminders.add(f"{event_name}_1h")
                        
                        elif 9.5 < minutes_left <= 10.5 and f"{event_name}_10m" not in sent_reminders:
                            for user in subs:
                                try: bot.send_message(user, f"🔔 *Напоминание за 10 минут!*\nДо старта '{event_name}' осталось 10 минут. Готовь чипсы! 🍿")
                                except: pass
                            sent_reminders.add(f"{event_name}_10m")
                        
                        elif -0.5 < minutes_left <= 0.5 and f"{event_name}_start" not in sent_reminders:
                            for user in subs:
                                try: bot.send_message(user, f"🏁 *СЕССИЯ НАЧАЛАСЬ!*\n'{event_name}' уже в эфире! 🏎️💨")
                                except: pass
                            sent_reminders.add(f"{event_name}_start")
            
            time.sleep(30)
        except Exception as e:
            print(f"Reminder Error: {e}")
            time.sleep(30)

threading.Thread(target=reminder_worker, daemon=True).start()

if __name__ == "__main__":
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print(f"Polling Error: {e}")
