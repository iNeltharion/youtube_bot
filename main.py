import yt_dlp
import subprocess
import os
import telebot
from dotenv import load_dotenv
import logging
import re
from urllib.parse import urlparse, urlunparse
from db import init_db, save_link
import show_handlers  # Импортируем весь модуль для регистрации хендлеров
from telebot import types

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

load_dotenv()
TOKEN = os.getenv('TOKEN')

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# ID администратора Telegram
ADMIN_ID = int(os.getenv('ADMIN_ID'))  # Укажите здесь свой Telegram ID

# Максимальная продолжительность видео в секундах (например, 15 минут)
MAX_DURATION = 15 * 60

# Функция для проверки и создания папок
def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Очистка URL от параметров
def clean_url(url):
    parsed = urlparse(url)
    return urlunparse(parsed._replace(query=""))

# Функция для получения информации о видео
def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,  # Отключаем вывод в консоль
            'outtmpl': '%(id)s.%(ext)s',  # Для отладки
            'extractor-args': ['youtube:formats=mp4'],  # Указываем формат mp4
            'noplaylist': True,  # Убедимся, что загружается только одно видео
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            logger.info(f"Информация о видео: {info['title']}")
            return info
    except Exception as e:
        logger.error(f"Ошибка получения информации о видео: {e}")
        return None

# Функция для скачивания аудио с YouTube
def download_audio(url, output_dir='temp'):
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'extractaudio': True,
        'noplaylist': True,  # Отключаем скачивание всего плейлиста
        'quiet': True,  # Отключаем вывод в консоль
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.info(f"Начинаем скачивание: {url}")
            ydl.download([url])
        logger.info("Загрузка завершена")

        # Путь к скачанному файлу
        downloaded_file = ydl.prepare_filename(ydl.extract_info(url, download=False))
        return os.path.join(output_dir, os.path.basename(downloaded_file))

    except Exception as e:
        logger.error(f"Ошибка загрузки: {e}")
        return None

# Функция для конвертации аудио в MP3
def convert_audio(input_file, output_file):
    try:
        subprocess.run(['ffmpeg', '-i', input_file, output_file], check=True)
        logger.info(f"Конвертация прошла успешно: {output_file}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка конвертации: {e}")

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_list = types.KeyboardButton("Список аудиозаписей")
    markup.add(btn_list)
    bot.reply_to(message, "Привет! Отправь ссылку на YouTube видео, и я отправлю тебе аудио.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "Список аудиозаписей")
def handle_list_button(message):
    import show_handlers
    show_handlers.list_telegram_audio(bot, message)

# Обработчик сообщений с ссылками
@bot.message_handler(func=lambda message: re.match(r'(https?://)?(www\.)?(m\.)?(youtube\.com|youtu\.be)/.+', message.text))
def handle_video(message):
    video_url = clean_url(message.text.strip())

    # Подтверждение получения ссылки
    bot.send_message(message.chat.id, "Получил ссылку! Начинаю скачивание аудио...")
    logger.info(f"Получена ссылка на видео: {video_url}")

    # Получаем информацию о видео
    video_info = get_video_info(video_url)

    if not video_info:
        bot.send_message(message.chat.id, "Не удалось получить информацию о видео. Попробуйте еще раз.")
        logger.error("Не удалось получить информацию о видео.")
        return

    # Проверяем длительность видео
    duration = video_info.get('duration', 0)
    logger.info(f"Продолжительность видео: {duration} секунд.")
    # Проверяем ограничение только для не-админов
    if message.from_user.id != ADMIN_ID and duration > MAX_DURATION:
        bot.send_message(
            message.chat.id,
            f"Видео слишком длинное! Максимальная продолжительность: {MAX_DURATION // 60} минут."
        )
        logger.error("Видео слишком длинное.")
        return

    # Создаем необходимые папки
    ensure_directory_exists('sound')
    ensure_directory_exists('temp')

    # Загружаем аудио
    downloaded_file = download_audio(video_url)

    if downloaded_file:
        # Генерация выходного пути для MP3 файла
        output_file = os.path.join('sound', os.path.splitext(os.path.basename(downloaded_file))[0] + '.mp3')

        # Отправляем сообщение о начале конвертации
        bot.send_message(message.chat.id, "Конвертируем аудио в формат MP3...")

        # Конвертируем в MP3
        convert_audio(downloaded_file, output_file)

        # Отправляем пользователю аудиофайл и сохраняем file_id
        with open(output_file, 'rb') as audio:
            sent = bot.send_audio(message.chat.id, audio)
            audio_file_id = sent.audio.file_id if sent.audio else None
            audio_title = sent.audio.title if sent.audio and sent.audio.title else os.path.splitext(os.path.basename(downloaded_file))[0]
            # Сохраняем file_id и название аудио в БД
            save_link(message.from_user, video_url, audio_file_id, audio_title)

        # Удаляем временные файлы
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)
            logger.info(f"Удаление временного файла: {downloaded_file}")
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.info(f"Удаление MP3 файла: {output_file}")

    else:
        bot.send_message(message.chat.id, "Не удалось скачать аудио с YouTube. Попробуйте еще раз.")

show_handlers.register_handlers(bot, ADMIN_ID)
# Запуск бота
if __name__ == "__main__":
    init_db()
    logging.info('Бот запущен')
    bot.polling(non_stop=True)
