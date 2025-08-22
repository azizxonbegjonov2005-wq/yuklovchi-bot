import datetime
import os
import re
import time
from urllib.parse import urlparse

import telebot
import yt_dlp
from telebot.util import quick_markup

# -------------------------
# BU YERNI O'ZGARTIRASAN
BOT_TOKEN = "8201513399:AAGHmovP8VcT1tdyswTW6VSKs-ImyxyjWPY"   # o'z tokeningni shu yerga yoz
OUTPUT_FOLDER = "downloads"                      # yuklab olingan fayllar papkasi
MAX_FILESIZE = 50000000                          # 50 MB (Telegram limitiga mos)
LOGS = None                                      # Agar log kanal kerak bo'lsa, kanal chat_id yoz
# -------------------------

# Papkani yaratib qo'yamiz agar bo'lmasa
if not os.path.exists(OUTPUT_FOLDER):
    os.makedirs(OUTPUT_FOLDER)

bot = telebot.TeleBot(BOT_TOKEN)
last_edited = {}


def youtube_url_validation(url):
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})')

    youtube_regex_match = re.match(youtube_regex, url)
    if youtube_regex_match:
        return youtube_regex_match

    return youtube_regex_match


@bot.message_handler(commands=['start', 'help'])
def test(message):
    bot.reply_to(
        message,
        "👋 *Salom!* \n\n"
        "📥 Menga kerakli bo'lgan *video linkini* yuboring, men sizga uni yuklab beraman.\n\n"
        "🎬 Qo‘llab-quvvatlanadigan saytlar: \n"
        "▫️ YouTube\n"
        "▫️ Twitter\n"
        "▫️ TikTok\n"
        "▫️ Instagram va boshqalar ✅",
        parse_mode="MARKDOWN",
        disable_web_page_preview=True
    )


def download_video(message, url, audio=False, format_id="mp4"):
    url_info = urlparse(url)
    if url_info.scheme:
        if url_info.netloc in ['www.youtube.com', 'youtu.be', 'youtube.com', 'youtu.be']:
            if not youtube_url_validation(url):
                bot.reply_to(message, 'Invalid URL')
                return

        def progress(d):
            if d['status'] == 'yuklanmoqda':
                try:
                    update = False

                    if last_edited.get(f"{message.chat.id}-{msg.message_id}"):
                        if (datetime.datetime.now() - last_edited[f"{message.chat.id}-{msg.message_id}"]).total_seconds() >= 5:
                            update = True
                    else:
                        update = True

                    if update:
                        perc = round(d['downloaded_bytes'] *
                                     100 / d['total_bytes'])
                        bot.edit_message_text(
                            chat_id=message.chat.id, message_id=msg.message_id, text=f"Downloading {d['info_dict']['title']}\n\n{perc}%")
                        last_edited[f"{message.chat.id}-{msg.message_id}"] = datetime.datetime.now()
                except Exception as e:
                    print(e)

        msg = bot.reply_to(message, 'yuklanmoqda...')
        video_title = round(time.time() * 1000)

        with yt_dlp.YoutubeDL({'format': format_id, 'outtmpl': f'{OUTPUT_FOLDER}/{video_title}.%(ext)s', 'progress_hooks': [progress], 'postprocessors': [{  # Extract audio using ffmpeg
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
        }] if audio else [], 'max_filesize': MAX_FILESIZE}) as ydl:
            info = ydl.extract_info(url, download=True)

            try:
                bot.edit_message_text(
                    chat_id=message.chat.id, message_id=msg.message_id, text='telegramdan yuborayabmiz...')
                # noinspection PyBroadException
                try:
                    if audio:
                        bot.send_audio(message.chat.id, open(
                            info['requested_downloads'][0]['filepath'], 'rb'), reply_to_message_id=message.message_id)

                    else:
                        width = info['requested_downloads'][0]['width']
                        height = info['requested_downloads'][0]['height']

                        bot.send_video(message.chat.id, open(
                            info['requested_downloads'][0]['filepath'], 'rb'), reply_to_message_id=message.message_id, width=width, height=height)
                    bot.delete_message(message.chat.id, msg.message_id)
                except Exception:
                    bot.edit_message_text(
                        chat_id=message.chat.id, message_id=msg.message_id, text=f"Couldn't send file, make sure it's supported by Telegram and it doesn't exceed *{round(MAX_FILESIZE / 1000000)}MB*", parse_mode="MARKDOWN")

            except Exception as e:
                if isinstance(e, yt_dlp.utils.DownloadError):
                    bot.edit_message_text(
                        'Invalid URL', message.chat.id, msg.message_id)
                else:
                    bot.edit_message_text(
                        f"There was an error downloading your video, make sure it doesn't exceed *{round(MAX_FILESIZE / 1000000)}MB*", message.chat.id, msg.message_id, parse_mode="MARKDOWN")
        for file in os.listdir(OUTPUT_FOLDER):
            if file.startswith(str(video_title)):
                os.remove(f'{OUTPUT_FOLDER}/{file}')
    else:
        bot.reply_to(message, 'Invalid URL')


def log(message, text: str, media: str):
    if LOGS:
        if message.chat.type == 'private':
            chat_info = "Private chat"
        else:
            chat_info = f"Group: *{message.chat.title}* (`{message.chat.id}`)"

        bot.send_message(
            LOGS, f"Download request ({media}) from @{message.from_user.username} ({message.from_user.id})\n\n{chat_info}\n\n{text}")


def get_text(message):
    if len(message.text.split(' ')) < 2:
        if message.reply_to_message and message.reply_to_message.text:
            return message.reply_to_message.text

        else:
            return None
    else:
        return message.text.split(' ')[1]


@bot.message_handler(commands=['download'])
def download_command(message):
    text = get_text(message)
    if not text:
        bot.reply_to(
            message, 'Invalid usage, use `/download url`', parse_mode="MARKDOWN")
        return

    log(message, text, 'video')
    download_video(message, text)


@bot.message_handler(commands=['audio'])
def download_audio_command(message):
    text = get_text(message)
    if not text:
        bot.reply_to(
            message, 'Invalid usage, use `/audio url`', parse_mode="MARKDOWN")
        return

    log(message, text, 'audio')
    download_video(message, text, True)


@bot.message_handler(commands=['custom'])
def custom(message):
    text = get_text(message)
    if not text:
        bot.reply_to(
            message, 'Invalid usage, use `/custom url`', parse_mode="MARKDOWN")
        return

    msg = bot.reply_to(message, 'Getting formats...')

    with yt_dlp.YoutubeDL() as ydl:
        info = ydl.extract_info(text, download=False)

    data = {f"{x['resolution']}.{x['ext']}": {
        'callback_data': f"{x['format_id']}"} for x in info['formats'] if x['video_ext'] != 'none'}

    markup = quick_markup(data, row_width=2)

    bot.delete_message(msg.chat.id, msg.message_id)
    bot.reply_to(message, "Choose a format", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    if call.from_user.id == call.message.reply_to_message.from_user.id:
        url = get_text(call.message.reply_to_message)
        bot.delete_message(call.message.chat.id, call.message.message_id)
        download_video(call.message.reply_to_message, url,
                       format_id=f"{call.data}+bestaudio")
    else:
        bot.answer_callback_query(call.id, "You didn't send the request")


@bot.message_handler(func=lambda m: True, content_types=["text", "pinned_message", "photo", "audio", "video", "location", "contact", "voice", "document"])
def handle_private_messages(message):
    text = message.text if message.text else message.caption if message.caption else None

    if message.chat.type == 'private':
        log(message, text, 'video')
        download_video(message, text)
        return


bot.infinity_polling()