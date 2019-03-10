from queue import Queue
from threading import Thread

import logging
import os
#  import json
from datetime import time
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, Filters, Updater
from bot import start, day_photo, epic_photo, mars_photo, error, \
                check_nasa_day_photo_updates, make_day_photo_context, \
                check_nasa_epic_updates, make_epic_context, \
                check_mars_rover_updates, TESTING

from flask import Flask, request

app = Flask(__name__)

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

bot_token = os.environ.get('BOT_TOKEN')



def get_info(bot, update):
    bot.send_message(chat_id=update.message.chat_id,
                     text=str(bot.get_webhook_info()))

def setup():
    bot = Bot(token=bot_token)
    update_queue = Queue()
    dispatcher = Dispatcher(bot, update_queue)
    """
    jq = dispatcher.job_queue
    jq.run_repeating(check_nasa_day_photo_updates, interval=3600, first=0,
                     context=make_day_photo_context(testing=TESTING))
    jq.run_repeating(check_nasa_epic_updates, interval=3600, first=10 if TESTING else 300,
                     context=make_epic_context(testing=TESTING))
    jq.run_daily(check_mars_rover_updates, time=time(23, 33),
                 context={'Curiosity': 2320,
                          'Opportunity': 5111,
                          'Spirit': 2208,
                          'all': ['Curiosity', 'Opportunity', 'Spirit']})
    """
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('day_photo', day_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('epic_photo', epic_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('mars', mars_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_error_handler(error)
    dispatcher.add_handler(CommandHandler('info', get_info, filters=Filters.user(username='@keikoobro')))
    s = bot.set_webhook(url='https://safe-ridge-16430.herokuapp.com/hook/' + bot_token)
    if s:
        print(s)
        logger.info('webhook setup ok')
    else:
        print(s)
        logger.info('webhook setup failed')

    thread = Thread(target=dispatcher.start, name='dispatcher')
    thread.start()

    return update_queue, bot


update_queue, bot = setup()


@app.route('/hook/' + bot_token, methods=['POST'])
def webhook():
    #  if request.json:
    update = Update.de_json(request.get_json(force=True), bot)
    logger.info('Update received! ' + str(update))
    update_queue.put(update)
    return 'OK'


@app.route('/', methods=['GET', 'POST'])
def index():
    return 'HOME'


if __name__ == '__main__':
    app.run(
            host='0.0.0.0',
            port=os.environ.get('PORT')
            )
