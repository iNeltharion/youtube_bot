import sqlite3
from telebot.util import smart_split

def list_telegram_audio(bot, message):
    conn = sqlite3.connect('youtube_bot.db')
    c = conn.cursor()
    c.execute('SELECT audio_title, audio_file_id FROM links WHERE audio_file_id IS NOT NULL ORDER BY id DESC')
    rows = c.fetchall()
    conn.close()
    if not rows:
        bot.reply_to(message, "Нет аудиозаписей, отправленных ботом в Telegram.")
        return
    for title, file_id in rows:
        caption = f"<b>{title or 'Без названия'}</b>"
        try:
            bot.send_audio(message.chat.id, file_id, caption=caption, parse_mode='HTML')
        except Exception as e:
            bot.send_message(message.chat.id, f"Ошибка отправки аудио: {title}")

def register_handlers(bot, admin_id):
    @bot.message_handler(commands=['show'])
    def show_db(message):
        if message.from_user.id != admin_id:
            bot.reply_to(message, "У вас нет доступа к этой команде.")
            return
        conn = sqlite3.connect('youtube_bot.db')
        c = conn.cursor()
        c.execute('SELECT telegram_id, username, first_name, last_name, link, created_at FROM links ORDER BY id DESC')
        rows = c.fetchall()
        conn.close()
        if not rows:
            bot.reply_to(message, "База данных пуста.")
            return
        msg = 'База данных:\n\n'
        for row in rows:
            msg += f"<b>ID:</b> {row[0]}\n"
            msg += f"<b>Username:</b> {row[1]}\n"
            msg += f"<b>Имя:</b> {row[2]}\n"
            msg += f"<b>Фамилия:</b> {row[3]}\n"
            msg += f"<b>Ссылка:</b> {row[4]}\n"
            msg += f"<b>Время:</b> {row[5]}\n"
            msg += "----------------------\n"
        # smart_split принимает только limit, а не chars_limit
        for part in smart_split(msg, 4000):
            bot.send_message(message.chat.id, part, parse_mode='HTML')

    @bot.message_handler(commands=['list'])
    def list_command(message):
        list_telegram_audio(bot, message)
