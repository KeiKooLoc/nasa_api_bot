import os
TESTING = False
conf = {
            'NASA_API_KEY': os.environ.get('NASA_API_KEY'),
            'BOT_TOKEN': os.environ.get('BOT_TOKEN') if TESTING else os.environ.get('BOT_TOKEN_TEST'),
            'CHANNEL_NAME': '@nasa_api_test' if TESTING else '@nasa_api',
            'ERROR_LOG': '@nasa_api_test',  # reports will be sent here
            'ADMIN': '@keikoobro'
       }
