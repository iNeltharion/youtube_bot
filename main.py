import yt_dlp
import subprocess
import os
import telebot
from dotenv import load_dotenv
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

load_dotenv()
TOKEN = os.getenv('TOKEN')

# Инициализация бота
bot = telebot.TeleBot(TOKEN)

# Максимальная продолжительность видео в секундах (например, 15 минут)
MAX_DURATION = 15 * 60

# Функция для проверки и создания папок
def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

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
    bot.reply_to(message, "Привет! Отправь ссылку на YouTube видео, и я отправлю тебе аудио.")

# Обработчик сообщений с ссылками
@bot.message_handler(func=lambda message: message.text.startswith('https://www.youtube.com/'))
def handle_video(message):
    video_url = message.text.strip()

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
    if duration > MAX_DURATION:
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

        # Отправляем пользователю аудиофайл
        with open(output_file, 'rb') as audio:
            bot.send_audio(message.chat.id, audio)

        # Удаляем временные файлы
        if os.path.exists(downloaded_file):
            os.remove(downloaded_file)
            logger.info(f"Удаление временного файла: {downloaded_file}")
        if os.path.exists(output_file):
            os.remove(output_file)
            logger.info(f"Удаление MP3 файла: {output_file}")

    else:
        bot.send_message(message.chat.id, "Не удалось скачать аудио с YouTube. Попробуйте еще раз.")

# Запуск бота
if __name__ == "__main__":
    logging.info('Бот запущен')
    bot.polling(non_stop=True)
