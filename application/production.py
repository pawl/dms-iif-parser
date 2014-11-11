import os

DEBUG = False
RELOAD = False
CSRF_ENABLED = True
SECRET_KEY = os.environ.get('SECRET_KEY')
SQLALCHEMY_DATABASE_URI = str(os.environ.get('DATABASE_URL'))
