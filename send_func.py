from telegram import ParseMode, InputMediaPhoto
from telegram.error import BadRequest
from random import randint
from config import conf

# channel_name = conf['CHANNEL_NAME']


def send_apod(bot, picture, chat_id):
    if picture['media_type'] == 'video':
        bot.send_message(chat_id=chat_id,
                         text='<b>Astronomy Picture of the Day: </b>'
                              '<b>{title} </b>'
                              '<code>{explanation} </code>'
                              '{url}'.format(title=picture['title'], url=picture['url'],
                                             explanation=picture['explanation']),
                         parse_mode=ParseMode.HTML)
    else:
        try:
            # sending photo in hd
            msg = bot.send_photo(chat_id=chat_id, photo=picture['hdurl'],
                                 caption='<b>Astronomy Picture of the Day: </b>'
                                         '<code>{}</code>'.format(picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=chat_id,
                             text='<code>{}</code>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)
        # except => sending photo not in hd
        except BadRequest:
            msg = bot.send_photo(chat_id=chat_id, photo=picture['url'],
                                 caption='<b>Astronomy picture of the day: </b>'
                                         '<code>{}</code>'.format(picture['title']),
                                 parse_mode=ParseMode.HTML)

            bot.send_message(chat_id=chat_id,
                             text='<code>{}</code>'.format(picture['explanation']),
                             parse_mode=ParseMode.HTML,
                             reply_to_message_id=msg.message_id)


def send_epic(bot, media_arr, chat_id):
    if 0 < len(media_arr) < 10:
        bot.send_media_group(chat_id=chat_id, media=media_arr)
    if len(media_arr) > 10:
        bot.send_media_group(chat_id=chat_id, media=media_arr[:10])
        bot.send_media_group(chat_id=chat_id, media=media_arr[10:])


def send_mars_photos(bot, pictures, chat_id):
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
        bot.send_media_group(chat_id=chat_id, media=arr,
                             disable_notification=True)
