import requests
from PIL import Image
from io import BytesIO
from telegram import InputMediaPhoto, ParseMode
from config import conf


# Astronomy Picture of the Day https://apod.nasa.gov/apod/astropix.html
def apod_req(bot, chat_id=None):
    picture = requests.get('https://api.nasa.gov/planetary/apod?'
                           'api_key={}'.format(conf['NASA_API_KEY']))
    if picture.status_code == 200:
        return picture.json()
    else:
        bot.send_message(chat_id=chat_id if chat_id else conf['ERROR_LOG'],
                         text='apod_req, {}'.format(picture.status_code))
        return False


# EPIC API https://epic.gsfc.nasa.gov/about/api
def get_last_epic_date_req(bot, chat_id=None):
    all_dates = requests.get('https://api.nasa.gov/EPIC/api'
                             '/natural/all?api_key={}'.format(conf['NASA_API_KEY']))
    if all_dates.status_code == 200:
        return all_dates.json()[0]['date']
    else:
        bot.send_message(chat_id=chat_id if chat_id else conf['ERROR_LOG'],
                         text='last_epic_date_req, {}'.format(all_dates.status_code))
        return False


def get_epic_images_req(bot, date, chat_id=None):
    all_images = requests.get('https://api.nasa.gov/EPIC/api/'
                              'natural/date/{}?api_key={}'.format(date, conf['NASA_API_KEY']))
    if all_images.status_code == 200:
        return all_images.json()
    else:
        bot.send_message(chat_id=chat_id if chat_id else conf['ERROR_LOG'],
                         text='epic_images_req, {}'.format(all_images.status_code))
        return False


def get_epic_media_arr(bot, date, all_images, chat_id=None):
    media_arr = []
    y_m_d = date.split('-')
    if all_images:
        for image in all_images:
            img = requests.get('https://api.nasa.gov/EPIC/archive/natural/'
                               '{year}/{month}/{day}/png/{photo_name}.png?'
                               'api_key={api_key}'.format(
                                year=y_m_d[0], month=y_m_d[1], day=y_m_d[2], photo_name=image['image'],
                                api_key=conf['NASA_API_KEY']))
            if img.status_code == 200:
                i = Image.open(BytesIO(img.content))
                bio = BytesIO()
                bio.name = 'image.jpeg'
                i.save(bio, 'JPEG')
                bio.seek(0)
                media_arr.append(InputMediaPhoto(media=bio,
                                                 caption='<code>date: </code><b>{}</b> '
                                                         '<code>time: </code><b>{}</b>'.format(
                                                              date, image['date'].split(' ')[1]),
                                                 parse_mode=ParseMode.HTML))
            else:
                bot.send_message(chat_id=chat_id if chat_id else conf['ERROR_LOG'],
                                 text='get_epic_media_arr, {}'.format(img.status_code))
    return media_arr


# Mars Rover Photos API https://github.com/chrisccerami/mars-photo-api
def get_mars_photos(bot, rover, sol, chat_id=None):
    pictures = requests.get('https://api.nasa.gov/mars-photos/api/v1/'
                            'rovers/{}/photos?'
                            'sol={}&'
                            'api_key={}'.format(rover, sol, conf['NASA_API_KEY']))
    if pictures.status_code == 200:
        return pictures.json()['photos']
    else:
        bot.send_message(chat_id=chat_id if chat_id else conf['ERROR_LOG'],
                         text='get_mars_photos, {}'.format(pictures.status_code))
        return False
