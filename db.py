import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('youtube_bot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            link TEXT,
            created_at TEXT,
            audio_file_id TEXT,
            audio_title TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_link(user, link, audio_file_id=None, audio_title=None):
    conn = sqlite3.connect('youtube_bot.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO links (telegram_id, username, first_name, last_name, link, created_at, audio_file_id, audio_title)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        user.id,
        user.username,
        user.first_name,
        user.last_name,
        link,
        datetime.now().isoformat(),
        audio_file_id,
        audio_title
    ))
    conn.commit()
    conn.close()
