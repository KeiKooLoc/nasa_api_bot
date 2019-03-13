from telegram.ext import Updater, CommandHandler, Filters
from telegram import Bot
from threading import Thread, Event
from random import randint
from datetime import timedelta, time
import logging
import requests
import os
import sys


from database import show_data, epic_table, mars_table, img_lib_table, img_lib_req_tags
from req import apod_req, get_last_epic_date_req, get_epic_images_req, get_epic_media_arr, get_mars_photos
from send_func import send_apod, send_epic, send_mars_photos
from config import conf, TESTING

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def start(bot, update):
    update.message.reply_text("Hi, I'm nasa_api admin bot.")


def apod(bot, update, args):
    picture = apod_req(bot, update.message.chat_id)
    if picture:
        if args:
            send_apod(bot, picture, update.message.chat_id)
        else:
            send_apod(bot, picture, conf['CHANNEL_NAME'])


def check_apod_updates(bot, job):
    picture = apod_req(bot)
    if picture:
        if job.context['date'] != picture['date']:
            job.context['date'] = picture['date']
            send_apod(bot, picture, conf['CHANNEL_NAME'])


# find out how can I stop job queue task if request failed !
def make_apod_context(bot, testing):
    picture = apod_req(bot)
    if picture:
        return {'date': ''} if testing else {'date': picture['date']}
    else:
        return {'date': ''} if testing else {'date': picture['date']}  # !


def epic(bot, update, args):
    chat_id = update.message.chat_id
    date = get_last_epic_date_req(bot, chat_id)
    if date:
        all_images = get_epic_images_req(bot, date, chat_id)
        media_arr = get_epic_media_arr(bot, date, all_images, chat_id)
        if args:
            send_epic(bot, media_arr, chat_id)
        else:
            send_epic(bot, media_arr, conf['CHANNEL_NAME'])


# test if i could check only the date and use job context for it
def check_epic_updates(bot, job):
    date = get_last_epic_date_req(bot)
    if date and job.context['date'] != date:
        job.context['date'] = date
        all_images = get_epic_images_req(bot, date)
        media_arr = get_epic_media_arr(bot, date, all_images)
        send_epic(bot, media_arr, conf['CHANNEL_NAME'])


# find out how can I interrupt job_queue iteration if request failed !
def make_epic_context(bot, testing):
    date = get_last_epic_date_req(bot)
    if date:
        return {'date': ''} if testing else {'date': date}
    else:
        return {'date': ''} if testing else {'date': date}  # !


def mars_photos(bot, update, args):
    context = {'Curiosity': 2320,
               'Opportunity': 5111,
               'Spirit': 2208,
               'all': ['Curiosity', 'Opportunity', 'Spirit']}
    rover = context['all'][randint(0, 2)]
    sol = randint(0, context[rover])
    pictures = get_mars_photos(bot, rover, sol)
    if pictures:
        if args:
            send_mars_photos(bot, pictures, update.message.chat_id)
        else:
            send_mars_photos(bot, pictures, conf['CHANNEL_NAME'])


def check_mars_photos_updates(bot, job):
    rover = job.context['all'][randint(0, 2)]
    sol = randint(0, job.context[rover])
    pictures = get_mars_photos(bot, rover, sol)
    if pictures:
        send_mars_photos(bot, pictures, conf['CHANNEL_NAME'])


def img_lib(bot, update):
    pass


"""
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
"""


def test_db_command(bot, update):
    show_data()


def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)


def main():
    bot = Bot(token=conf['BOT_TOKEN'])
    updater = Updater(token=conf['BOT_TOKEN'])
    dp = updater.dispatcher
    jq = updater.job_queue

    # Commands for admin
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CommandHandler('apod', apod, pass_args=True,
                                  filters=Filters.user(username=conf['ADMIN'])))
    dp.add_handler(CommandHandler('epic', epic, pass_args=True,
                                  filters=Filters.user(username=conf['ADMIN'])))
    dp.add_handler(CommandHandler('mars', mars_photos, pass_args=True,
                                  filters=Filters.user(username=conf['ADMIN'])))
    dp.add_handler(CommandHandler('db', test_db_command,
                                  filters=Filters.user(username=conf['ADMIN'])))
    dp.add_error_handler(error)

    #
    jq.run_repeating(check_apod_updates, interval=3600, first=0,
                     context=make_apod_context(bot, TESTING))
    jq.run_repeating(check_epic_updates, interval=3600, first=15 if TESTING else 500,
                     context=make_epic_context(bot, TESTING))
    jq.run_daily(check_mars_photos_updates, time=time(9),
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
                                  filters=Filters.user(username=conf['ADMIN'])))

    if bot.get_webhook_info()['url']:
        bot.set_webhook()

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
