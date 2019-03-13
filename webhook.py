from queue import Queue
from threading import Thread
from flask import Flask, request

import logging
import os
from datetime import time
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, Filters, JobQueue
from bot import start, apod, epic, mars_photos, error, \
    check_apod_updates, make_apod_context, \
    check_epic_updates, make_epic_context, \
    check_mars_photos_updates, test_db_command, TESTING
from config import conf


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_info(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=str(bot.get_webhook_info()))


def setup():
    bot = Bot(token=conf['BOT_TOKEN'])
    update_queue = Queue()
    dp = Dispatcher(bot, update_queue)
    jq = JobQueue(bot)

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

    s = bot.set_webhook(url='https://salty-escarpment-89606.herokuapp.com/hook/' + conf['BOT_TOKEN'])
    if s:
        print(s)
        logger.info('webhook setup ok')
    else:
        print(s)
        logger.info('webhook setup failed')

    thread = Thread(target=dp.start, name='dispatcher')
    thread.start()
    jq.start()

    return update_queue, bot


update_queue, bot = setup()

app = Flask(__name__)


@app.route('/hook/' + conf['BOT_TOKEN'], methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = Update.de_json(request.get_json(force=True), bot)
        logger.info('Update received! ' + str(update))
        update_queue.put(update)
    return 'OK'


@app.route('/', methods=['GET', 'POST'])
def index():
    return 'HOME!'


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=os.environ.get('PORT'))
