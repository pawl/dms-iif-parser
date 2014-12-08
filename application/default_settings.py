import os

# Get application base dir.
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True
RELOAD = True
SECRET_KEY = 'mysecretkeyvalue'
SQLALCHEMY_DATABASE_URI = 'sqlite:////' + os.path.join(_basedir, 'app_dev.db')
QB_KEY = os.environ['QB_KEY']
QB_SECRET = os.environ['QB_SECRET']
QB_TOKEN = os.environ['QB_TOKEN']
QB_CALLBACK_URL = 'http://www.pptoqb.com/oauth_callback/'