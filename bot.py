import logging
from telegram.ext import Updater, CommandHandler
from telegram import ParseMode
from telegram.error import BadRequest
import requests
from PIL import Image
from io import BytesIO
import os

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


nasa_api_key = os.environ.get('NASA_API_KEY')
bot_token = os.environ.get('BOT_TOKEN')
channel_name = '@nasa_api'

def start(bot, update):
    update.message.reply_text("Hi, I'm nasa admin bot. "
                              "I'm post fresh information "
                              "to the @nasa_api channel. "
                              "We got next topics:"
                              "1) Astronomy Picture of the Day,"
                              "https://apod.nasa.gov/apod/astropix.html"
                              "2)EPIC API"
                              "https://epic.gsfc.nasa.gov/")


def search_and_send_epic_photo(bot, context):
    all_images = requests.get('https://api.nasa.gov/EPIC/api/'
                              'natural/date/{}?api_key={}'.format(
        context['date'], nasa_api_key)).json()
    for image in all_images:
        if image['image'] not in context['photo_names']:
            context['photo_names'][image['image']] = \
                image['date'].split(' ')[1]
            img = requests.get('https://api.nasa.gov/'
                               'EPIC/archive/natural/'
                               '{year}/'
                               '{month}/'
                               '{day}/png/'
                               '{photo_name}.png?'
                               'api_key={api_key}'.format(
                                    year=context['date'].split('-')[0],
                                    month=context['date'].split('-')[1],
                                    day=context['date'].split('-')[2],
                                    photo_name=image['image'],
                                    api_key=nasa_api_key))
            i = Image.open(BytesIO(img.content))
            bio = BytesIO()
            bio.name = 'image.jpeg'
            i.save(bio, 'JPEG')
            bio.seek(0)
            bot.send_photo(chat_id=channel_name, photo=bio,
                           caption='date: {}, time:{}'.format(
                               context['date'],
                               context['photo_names'][image['image']]))


def check_nasa_epic_updates(bot, job):
    # take the last day for available photos
    dates = requests.get('https://api.nasa.gov/EPIC/api'
                         '/natural/all?api_key={}'.format(
                            nasa_api_key)).json()
    date = dates[0]['date']
    if job.context['date'] != date:
        job.context['date'] = date
        job.context['photo_names'] = {}
        search_and_send_epic_photo(bot, job.context)
    else:
        search_and_send_epic_photo(bot, job.context)


def check_nasa_day_photo(bot, job):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(nasa_api_key)).json()
    if job.context['date'] != picture['date']:
        job.context['date'] = picture['date']
        try:
            # sending photo in hd
            bot.send_photo(chat_id=channel_name, photo=picture['hdurl'],
                           caption='<b>{}</b>'.format(picture['title']),
                           parse_mode=ParseMode.HTML)
            bot.send_message(chat_id=channel_name,
                             text='<i>{}</i>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML)
        # else sending photo not in hd
        except BadRequest:
            bot.send_photo(chat_id=channel_name, photo=picture['url'],
                           caption='<b>{}</b>'.format(picture['title']),
                           parse_mode=ParseMode.HTML
                           )
            bot.send_message(chat_id=channel_name,
                             text='<i>{}</i>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML)


def main():
    updater = Updater(token=bot_token)
    dp = updater.dispatcher
    j = updater.job_queue

    dp.add_handler(CommandHandler('start', start))

    j.run_repeating(check_nasa_epic_updates, interval=1000, first=10,
                    context={'date': '',
                             'photo_names': {}})

    j.run_repeating(check_nasa_day_photo, interval=2000, first=0,
                    context={'date': ''})

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
