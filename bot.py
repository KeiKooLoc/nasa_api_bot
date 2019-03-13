from PIL import Image
from io import BytesIO
from telegram.ext import Updater, CommandHandler, Filters
from telegram.error import BadRequest
from telegram import ParseMode, InputMediaPhoto, Message, Bot
from threading import Thread, Event
from random import randint
from datetime import timedelta, time
import logging
import requests
import os
import sys
from time import sleep
import pickle
from database import show_data, img_lib_req_tags, \
    epic_table, mars_table, img_lib_table

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
nasa_api_key = os.environ.get('NASA_API_KEY')
bot_token = os.environ.get('BOT_TOKEN')
TESTING = True

channel_name = '@nasa_api_test' if TESTING else '@nasa_api'


def start(bot, update):
    update.message.reply_text("Hi, I'm nasa admin bot. "
                              """ 
                              "I'm post fresh information "
                              "to the @nasa_api channel. "
                              "We got next topics: "
                              "1) Astronomy Picture of the Day, "
                              "https://apod.nasa.gov/apod/astropix.html, "
                              "2)EPIC API "
                              "https://epic.gsfc.nasa.gov/,"
                              """
                              )


def send_apod(bot, picture, update=None):
    address = channel_name
    if update:
        address = update.message.chat_id
    if picture['media_type'] == 'video':
        bot.send_message(chat_id=address,
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
            msg = bot.send_photo(chat_id=address, photo=picture['hdurl'],
                                 caption='<b>Astronomy Picture of the Day: </b>'
                                         '<code>{}</code>'.format(picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=address,
                             text='<code>{}</code>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)
        # else sending photo not in hd
        except BadRequest:
            msg = bot.send_photo(chat_id=address, photo=picture['url'],
                                 caption='<b>Astronomy picture of the day: </b>'
                                         '<code>{}</code>'.format(
                                             picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=address,
                             text='<code>{}</code>'.format(
                                      picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)


def apod(bot, update, args):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(nasa_api_key))
    if picture.status_code == 200:
        if args:
            send_apod(bot, picture.json(), update=update)
        else:
            send_apod(bot, picture.json())
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='def apod() | status: {}'.format(
                             picture.status_code))


def check_apod_updates(bot, job):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(nasa_api_key))
    if picture.status_code == 200:
        if job.context['date'] != picture.json()['date']:
            job.context['date'] = picture.json()['date']
            send_apod(bot, picture.json())
    else:
        bot.send_message(chat_id='@nasa_api_test',
                         text='check_apod_updates() | status: {}'.format(
                             picture.status_code))


def make_apod_context(testing=False):
    if testing:
        return {'date': ''}
    return {'date': requests.get('https://api.nasa.gov/planetary/apod?'
                                 'api_key={}'.format(nasa_api_key)).json()['date']}


def send_epic(bot, context, update=None):
    all_images = requests.get('https://api.nasa.gov/EPIC/api/'
                              'natural/date/{}?api_key={}'.format(
                               context['date'], nasa_api_key))
    if all_images.status_code == 200:
        arr = []
        for image in all_images.json():
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
                if img.status_code == 200:
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
                else:
                    bot.send_message(chat_id='@nasa_api_test',
                                     text='send_epic_photo(), img | status: {}'.format(
                                         img.status_code))
        if len(arr) > 0:
            if update:
                try:
                    bot.send_media_group(chat_id=update.message.chat_id, media=arr)
                except BadRequest:
                    bot.send_media_group(chat_id=update.message.chat_id, media=arr[:10])
                    bot.send_media_group(chat_id=update.message.chat_id, media=arr[10:])
            else:
                try:
                    bot.send_media_group(chat_id=channel_name, media=arr)
                except BadRequest:
                    bot.send_media_group(chat_id=channel_name, media=arr[:10])
                    bot.send_media_group(chat_id=channel_name, media=arr[10:])
    else:
        bot.send_message(chat_id='@nasa_api_test',
                         text='def send_epic(), all_images | status: {}'.format(
                             all_images.status_code))


def epic(bot, update, args):
    dates = requests.get('https://api.nasa.gov/EPIC/api'
                         '/natural/all?api_key={}'.format(
                              nasa_api_key))
    if dates.status_code == 200:
        date = dates.json()[0]['date']
        if args:
            send_epic(bot, context={'date': date,
                                    'photo_names': {}},
                      update=update)
        else:
            send_epic(bot, context={'date': date,
                                    'photo_names': {}})
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='def epic() | status: {}'.format(
                                         dates.status_code))


# test if i could check only the date and use job context for it
def check_epic_updates(bot, job):
    # take the last day for available photos
    dates = requests.get('https://api.nasa.gov/EPIC/api'
                         '/natural/all?api_key={}'.format(
                            nasa_api_key))
    if dates.status_code == 200:
        date = dates.json()[0]['date']
        if job.context['date'] != date:
            job.context['date'] = date
            job.context['photo_names'] = {}
            send_epic(bot, job.context)
        else:
            send_epic(bot, job.context)
    else:
        bot.send_message(chat_id='@nasa_api_test',
                         text='def check_nasa_epic_updates() | status: {}'.format(
                                         dates.status_code))


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


def send_mars_photos(bot, pictures, update=None):
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
        if update:
            bot.send_media_group(chat_id=update.message.chat_id, media=arr,
                                 disable_notification=True)
        else:
            bot.send_media_group(chat_id=channel_name, media=arr,
                                 disable_notification=True)


def mars_photos(bot, update, args):
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
                                nasa_api_key))
    if pictures.status_code == 200:
        if args:
            send_mars_photos(bot, pictures.json()['photos'], update=update)
        else:
            send_mars_photos(bot, pictures.json()['photos'])
    else:
        bot.send_message(chat_id=update.message.chat_id,
                         text='mars_photo() | status: {}'.format(
                                         pictures.status_code))


def check_mars_photos_updates(bot, job):
    rover = job.context['all'][randint(0, 2)]
    pictures = requests.get('https://api.nasa.gov/mars-photos/api/v1/'
                            'rovers/{}/photos?'
                            'sol={}&'
                            'api_key={}'.format(
                                rover,
                                randint(1, job.context[rover]),
                                nasa_api_key))
    if pictures.status_code == 200:
        send_mars_photos(bot, pictures.json()['photos'])
    else:
        bot.send_message(chat_id='@nasa_api_test',
                         text='check_mars_photos_updates() | status: {}'.format(
                                         pictures.status_code))


def img_lib(bot, update):
    pass


def check_img_lib_updates(bot, job):
    pictures = requests.get('https://images-api.nasa.gov/search?'
                            'q={}&'
                            'media_type=image'.format(
                                img_lib_req_tags[randint(0, len(img_lib_req_tags) - 1)]))
    if pictures.status_code == 200:
        for i in pictures.json()['collection']['items']:
            img_in_db = img_lib_table.find_one({'nasa_id': str(i['data'][0]['nasa_id'])})
            if not img_in_db:
                img_lib_table.insert_one({'nasa_id': str(i['data'][0]['nasa_id'])})
    else:
        bot.send_message(chat_id='@nasa_api_test',
                         text='def check_img_lib_updates() | status: {}'.format(
                                         pictures.status_code))
    pass


def test_db_command(bot, update):
    show_data()


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    bot = Bot(token=bot_token)
    updater = Updater(token=bot_token)
    dp = updater.dispatcher
    jq = updater.job_queue

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('apod', apod, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_handler(CommandHandler('epic', epic, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_handler(CommandHandler('mars', mars_photos, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dp.add_error_handler(error)

    dp.add_handler(CommandHandler('db', test_db_command,))

    jq.run_repeating(check_apod_updates, interval=3600, first=0,
                     context=make_apod_context(testing=TESTING))
    jq.run_repeating(check_epic_updates, interval=3600, first=10 if TESTING else 300,
                     context=make_epic_context(testing=TESTING))
    jq.run_daily(check_mars_photos_updates, time=time(17, 30),
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

    if bot.get_webhook_info()['url']:
        bot.set_webhook()

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
