import os

DEBUG = False
RELOAD = False
CSRF_ENABLED = True
SECRET_KEY = os.environ.get('SECRET_KEY')
SQLALCHEMY_DATABASE_URI = str(os.environ.get('DATABASE_URL'))
QB_KEY = os.environ['QB_KEY']
QB_SECRET = os.environ['QB_SECRET']
QB_TOKEN = os.environ['QB_TOKEN']
QB_CALLBACK_URL = 'http://www.pptoqb.com/oauth_callback/'