from queue import Queue
from threading import Thread

import logging
import os
import json
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, Filters
from bot import start, day_photo, epic_photo, mars_photo, error



logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot_token = os.environ.get('BOT_TOKEN')
bot = Bot(token=bot_token)
update_queue = Queue()
dispatcher = Dispatcher(bot, update_queue)


def setup():
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('day_photo', day_photo, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('epic_photo', epic_photo, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('mars', mars_photo, pass_args=True,
                                  filters=Filters.user(username='@keikoobro')))
    dispatcher.add_error_handler(error)

    thread = Thread(target=dispatcher.start, name='dispatcher')
    thread.start()

    return update_queue


def webhook(update):
    update_queue.put(Update.de_json(json.loads(update), bot))


def set_webhook():
    s = bot.set_webhook('https://safe-ridge-16430.herokuapp.com/' + bot_token)
    if s:
        print(s)
        logger.info('webhook setup ok')
    else:
        print(s)
        logger.info('webhook setup failed')

set_webhook()

setup()
set_webhook()
