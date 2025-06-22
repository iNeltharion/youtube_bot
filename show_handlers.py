import sqlite3

def register_handlers(bot, admin_id):
    @bot.message_handler(commands=['show'])
    def show_db(message):
        if message.from_user.id != admin_id:
            bot.reply_to(message, "У вас нет доступа к этой команде.")
            return
        conn = sqlite3.connect('youtube_bot.db')
        c = conn.cursor()
        c.execute('SELECT telegram_id, username, first_name, last_name, link, created_at FROM links ORDER BY id DESC LIMIT 20')
        rows = c.fetchall()
        conn.close()
        if not rows:
            bot.reply_to(message, "База данных пуста.")
            return
        msg = '<b>Последние 20 записей:</b>\n\n'
        for row in rows:
            msg += f"<b>ID:</b> {row[0]}\n"
            msg += f"<b>Username:</b> {row[1]}\n"
            msg += f"<b>Имя:</b> {row[2]}\n"
            msg += f"<b>Фамилия:</b> {row[3]}\n"
            msg += f"<b>Ссылка:</b> {row[4]}\n"
            msg += f"<b>Время:</b> {row[5]}\n"
            msg += "----------------------\n"
        bot.send_message(message.chat.id, msg, parse_mode='HTML')

