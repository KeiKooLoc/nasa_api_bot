from queue import Queue
from threading import Thread
from flask import Flask, request

import logging
import os
from datetime import time
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, Filters, JobQueue
from bot import start, day_photo, epic_photo, mars_photo, error, \
    check_nasa_day_photo_updates, make_day_photo_context, \
    check_nasa_epic_updates, make_epic_context, \
    check_mars_rover_updates, TESTING



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
    job_queue = JobQueue(bot)

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('day_photo', day_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('epic_photo', epic_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_handler(CommandHandler('mars', mars_photo, pass_args=True,
                                          filters=Filters.user(username='@keikoobro')))
    dispatcher.add_error_handler(error)
    dispatcher.add_handler(CommandHandler('info', get_info,
                                          filters=Filters.user(username='@keikoobro')))

    job_queue.run_repeating(check_nasa_day_photo_updates, interval=3600, first=0,
                            context=make_day_photo_context(testing=TESTING))
    job_queue.run_repeating(check_nasa_epic_updates, interval=3600, first=6000 if TESTING else 500,
                            context=make_epic_context(testing=TESTING))
    job_queue.run_daily(check_mars_rover_updates, time=time(17),
                        context={'Curiosity': 2320,
                                 'Opportunity': 5111,
                                 'Spirit': 2208,
                                 'all': ['Curiosity', 'Opportunity', 'Spirit']})

    s = bot.set_webhook(url='https://safe-ridge-16430.herokuapp.com/hook/' + bot_token)
    if s:
        print(s)
        logger.info('webhook setup ok')
    else:
        print(s)
        logger.info('webhook setup failed')

    thread = Thread(target=dispatcher.start, name='dispatcher')
    thread.start()
    job_queue.start()

    return update_queue, bot


update_queue, bot = setup()

app = Flask(__name__)


@app.route('/hook/' + bot_token, methods=['POST'])
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
