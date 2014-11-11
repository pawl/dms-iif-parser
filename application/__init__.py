from flask import Flask, render_template, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.admin import Admin

# Create the app and configuration
# Read the configuration file
app = Flask(__name__)
app.config.from_object('application.default_settings')
app.config.from_envvar('PRODUCTION_SETTINGS', silent=True)

# Connect to database with sqlalchemy.
db = SQLAlchemy(app)

from application.models import *
from application.views import *

admin = Admin(app, name='IIF Parser', static_url_path="/assets", template_mode="bootstrap3", index_view=HomeView(name='Secret Key', template='home.html', url='/'))
admin.add_view(Upload(name='Upload/Parse'))
admin.add_view(RulesView(Rule, db.session, name="Rules"))