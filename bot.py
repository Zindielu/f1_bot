import telebot
import time
import threading
from datetime import datetime

# ВСТАВЬ СЮДА СВОЙ ТОКЕН МЕЖДУ КАВЫЧКАМИ
BOT_TOKEN = "9023464869:AAG7tjtHT0msE1bvkb_U00ucfOvfGJgSuak"
bot = telebot.TeleBot(BOT_TOKEN)

# --- СПИСОК ВСЕХ СОБЫТИЙ ---
RACES = [
    # --- Гран-при Катара (27-29 ноября 2026) ---
    (2026, 11, 27, 16, 30, "Практика 1 (Катар)"),
    (2026, 11, 27, 20, 0, "Практика 2 (Катар)"),
    (2026, 11, 28, 17, 30, "Практика 3 (Катар)"),
    (2026, 11, 28, 21, 0, "Квалификация (Катар)"),
    (2026, 11, 29, 19, 0, "🏁 ГОНКА: Гран-при Катара"),
    
    # --- Гран-при Абу-Даби (финал сезона) ---
    (2026, 12, 6, 16, 0, "🏁 ГОНКА: Гран-при Абу-Даби")
]

# Хранилища (в памяти)
subscribers = set()
sent_reminders = set()

# --- ХЭНДЛЕРЫ (КОМАНДЫ) ---
@bot.message_handler(commands=['start'])
def start_message(message):
    subscribers.add(message.chat.id)
    bot.send_message(message.chat.id, 
        "Привет! Я бот-напоминалка Ф1. 🏎️\n\n"
        "Я знаю расписание практик, квалификаций и гонок.\n"
        "Напиши /next, чтобы узнать ближайшую сессию, или /subscribe, чтобы получать уведомления.")

@bot.message_handler(commands=['subscribe'])
def subscribe(message):
    subscribers.add(message.chat.id)
    bot.send_message(message.chat.id, "✅ Ты подписан! Я пришлю сообщение за 10 минут до каждой сессии.")

@bot.message_handler(commands=['next'])
def next_race(message):
    now = datetime.now()
    upcoming = []
    for race in RACES:
        race_date = datetime(race[0], race[1], race[2], race[3], race[4])
        if race_date > now:
            upcoming.append((race_date, race[5]))
    
    if not upcoming:
        bot.send_message(message.chat.id, "Пока нет будущих событий.")
        return
    
    upcoming.sort(key=lambda x: x[0])
    next_date, next_name = upcoming[0]
    
    delta = next_date - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    text = f"🏁 Ближайшее событие: *{next_name}*\n"
    text += f"📅 Старт: {next_date.strftime('%d.%m.%Y в %H:%M')}\n"
    text += f"⏳ Осталось: {days} д. {hours} ч. {minutes} мин."
    bot.send_message(message.chat.id, text, parse_mode='Markdown')

# --- ФУНКЦИЯ АВТОМАТИЧЕСКИХ НАПОМИНАНИЙ ---
def check_races():
    while True:
        now = datetime.now()
        for race in RACES:
            race_date = datetime(race[0], race[1], race[2], race[3], race[4])
            delta = race_date - now
            minutes_left = delta.total_seconds() / 60
            
            # Если до события осталось 10 минут (или меньше) и мы еще не напоминали
            if 0 < minutes_left <= 10 and race[5] not in sent_reminders:
                for chat_id in subscribers:
                    try:
                        bot.send_message(chat_id, f"🔔 *Напоминание!*\nДо старта '{race[5]}' осталось 10 минут!", parse_mode='Markdown')
                    except:
                        pass
                sent_reminders.add(race[5])
                
        time.sleep(30) # Проверяем каждые 30 секунд

# --- ЗАПУСК ---
threading.Thread(target=check_races, daemon=True).start() # Запускаем проверку времени

print("Бот запущен и ждет сообщений...")
bot.polling(none_stop=True)
