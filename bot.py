from PIL import Image
from io import BytesIO
from telegram.ext import Updater, CommandHandler, Filters
from telegram.error import BadRequest
from telegram import ParseMode, InputMediaPhoto, Message
from threading import Thread, Event
from random import randint
from time import time
from datetime import timedelta
import logging
import requests
import os
import sys
from time import sleep
import pickle


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)
nasa_api_key = os.environ.get('NASA_API_KEY')
bot_token = os.environ.get('BOT_TOKEN')
TESTING = False

channel_name = '@nasa_api_test' if TESTING else '@nasa_api'


def start(bot, update):
    update.message.reply_text("Hi, I'm nasa admin bot. "
                              "I'm post fresh information "
                              "to the @nasa_api channel. "
                              "We got next topics: "
                              "1) Astronomy Picture of the Day, "
                              "https://apod.nasa.gov/apod/astropix.html, "
                              "/day_photo "
                              "2)EPIC API "
                              "https://epic.gsfc.nasa.gov/, "
                              "/epic_photo")


def send_day_photo(bot, picture):
    # sending video
    if picture['media_type'] == 'video':
        bot.send_message(chat_id=channel_name,
                         text='<b>Astronomy Picture of the Day: </b>'
                              '<b>{title} </b>'
                              '<code>{explanation} </code>'
                              '{url}'.format(
                                  title=picture['title'],
                                  url=picture['url'],
                                  explanation=picture['explanation']),
                         parse_mode=ParseMode.HTML)
    else:
        try:
            # sending photo in hd
            msg = bot.send_photo(chat_id=channel_name, photo=picture['hdurl'],
                                 caption='<b>Astronomy Picture of the Day: </b>'
                                         '<code>{}</code>'.format(picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=channel_name,
                             text='<code>{}</code>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)
        # else sending photo not in hd
        except BadRequest:
            msg = bot.send_photo(chat_id=channel_name, photo=picture['url'],
                                 caption='<b>Astronomy picture of the day: </b>'
                                         '<code>{}</code>'.format(
                                             picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=channel_name,
                             text='<code>{}</code>'.format(
                                      picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)


def day_photo(bot, update):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(nasa_api_key))
    if picture.status_code == 200:
        send_day_photo(bot, picture.json())
    else:
        bot.send_message(chat_id='@keikoobro',
                         text='day_photo() | status: {}'.format(
                             picture.status_code))


def check_nasa_day_photo_updates(bot, job):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(nasa_api_key))
    if picture.status_code == 200:
        if job.context['date'] != picture.json()['date']:
            job.context['date'] = picture.json()['date']
            send_day_photo(bot, picture.json())
    else:
        bot.send_message(chat_id='@keikoobro',
                         text='check_nasa_day_photo_updates() | status: {}'.format(
                             picture.status_code))


def make_day_photo_context(testing=False):
    if testing:
        return {'date': ''}
    return {'date': requests.get('https://api.nasa.gov/planetary/apod?'
                                 'api_key={}'.format(nasa_api_key)).json()['date']}


def send_epic_photo(bot, context):
    all_images = requests.get('https://api.nasa.gov/EPIC/api/'
                              'natural/date/{}?api_key={}'.format(
                               context['date'], nasa_api_key)).json()
    arr = []
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
            arr.append(InputMediaPhoto(media=bio,
                                       caption='<code>date: </code><b>{}</b> '
                                               '<code>time: </code><b>{}</b>'.format(
                                                context['date'],
                                                context['photo_names'][image['image']]),
                                       parse_mode=ParseMode.HTML))
    if len(arr) > 0:
        try:
            bot.send_media_group(chat_id=channel_name, media=arr)
        except BadRequest:
            bot.send_media_group(chat_id=channel_name, media=arr[:10])
            bot.send_media_group(chat_id=channel_name, media=arr[10:])


def epic_photo(bot, update):
    dates = requests.get('https://api.nasa.gov/EPIC/api'
                         '/natural/all?api_key={}'.format(
                              nasa_api_key)).json()
    date = dates[0]['date']
    send_epic_photo(bot, context={'date': date,
                                  'photo_names': {}})


def check_nasa_epic_updates(bot, job):
    # take the last day for available photos
    dates = requests.get('https://api.nasa.gov/EPIC/api'
                         '/natural/all?api_key={}'.format(
                            nasa_api_key)).json()
    date = dates[0]['date']
    if job.context['date'] != date:
        job.context['date'] = date
        job.context['photo_names'] = {}
        send_epic_photo(bot, job.context)
    else:
        send_epic_photo(bot, job.context)


def make_epic_context(testing=False):
    if testing:
        return {'date': '',
                'photo_names': {}}
    context = {'date': requests.get('https://api.nasa.gov/EPIC/api'
                                    '/natural/all?api_key={}'.format(
                                        nasa_api_key)).json()[0]['date'],
               'photo_names': {}}
    all_images = requests.get('https://api.nasa.gov/EPIC/api/'
                              'natural/date/{}?api_key={}'.format(
                               context['date'], nasa_api_key)).json()
    for image in all_images:
        if image['image'] not in context['photo_names']:
            context['photo_names'][image['image']] = \
                image['date'].split(' ')[1]
    return context


def send_mars_photo(bot, pictures):
    arr = []
    if len(pictures) > 5:
        for i in range(5):
            img = pictures[randint(0, len(pictures) - 1)]
            arr.append(InputMediaPhoto(media=img['img_src'],
                                       caption='<code>Mars rover: </code><b>{}</b>, '
                                               '<code>Earth date: </code><b>{}</b>, '
                                               '<code>Sol: </code><b>{}</b>, '
                                               '<code>Camera: </code><b>{}</b>'.format(
                                           img['rover']['name'], img['earth_date'],
                                           img['sol'], img['camera']['full_name']),
                                       parse_mode=ParseMode.HTML))
    else:
        for img in pictures:
            arr.append(InputMediaPhoto(media=img['img_src'],
                                       caption='<code>Mars rover: </code><b>{}</b>, '
                                               '<code>Earth date: </code><b>{}</b>, '
                                               '<code>Sol: </code><b>{}</b>, '
                                               '<code>Camera: </code><b>{}</b>'.format(
                                           img['rover']['name'], img['earth_date'],
                                           img['sol'], img['camera']['full_name']),
                                       parse_mode=ParseMode.HTML))
    if len(arr) > 0:
        bot.send_media_group(chat_id=channel_name, media=arr)


def mars_photo(bot, update):
    context = {'Curiosity': 2320,
               'Opportunity': 5111,
               'Spirit': 2208,
               'all': ['Curiosity', 'Opportunity', 'Spirit']}
    rover = context['all'][randint(0, 2)]
    pictures = requests.get('https://api.nasa.gov/mars-photos/api/v1/'
                            'rovers/{}/photos?'
                            'sol={}&'
                            'api_key={}'.format(
                                rover,
                                randint(1, context[rover]),
                                nasa_api_key)).json()['photos']
    send_mars_photo(bot, pictures)


def check_mars_rover_updates(bot, job):
    rover = job.context['all'][randint(0, 2)]
    pictures = requests.get('https://api.nasa.gov/mars-photos/api/v1/'
                            'rovers/{}/photos?'
                            'sol={}&'
                            'api_key={}'.format(
                                rover,
                                randint(1, job.context[rover]),
                                nasa_api_key)).json()['photos']
    send_mars_photo(bot, pictures)


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    updater = Updater(token=bot_token)
    dp = updater.dispatcher
    jq = updater.job_queue

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('day_photo', day_photo,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_handler(CommandHandler('epic_photo', epic_photo,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_handler(CommandHandler('mars', mars_photo,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_error_handler(error)

    jq.run_repeating(check_nasa_day_photo_updates, interval=3600, first=0,
                     context=make_day_photo_context(testing=TESTING))
    jq.run_repeating(check_nasa_epic_updates, interval=3600, first=10 if TESTING else 300,
                     context=make_epic_context(testing=TESTING))
    jq.run_repeating(check_mars_rover_updates, interval=25000, first=70 if TESTING else 25000,
                     context={'Curiosity': 2320,
                              'Opportunity': 5111,
                              'Spirit': 2208,
                              'all': ['Curiosity', 'Opportunity', 'Spirit']})
    
    def stop_and_restart():
        updater.stop()
        os.execl(sys.executable, sys.executable, *sys.argv)

    def restart(bot, update):
        update.message.reply_text('Bot is restarting...')
        Thread(target=stop_and_restart).start()

    dp.add_handler(CommandHandler('r', restart,
                                  filters=Filters.user(username='@keikoobro')))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
