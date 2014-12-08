from flask import Flask, render_template, session
from flask.ext.sqlalchemy import SQLAlchemy
from flask.ext.admin.base import MenuLink, Admin

# Create the app and configuration
# Read the configuration file
app = Flask(__name__)
app.config.from_object('application.default_settings')
app.config.from_envvar('PRODUCTION_SETTINGS', silent=True)

# log to papertrail in heroku
if not app.debug:
	import logging
	app.logger.addHandler(logging.StreamHandler())
	app.logger.setLevel(logging.INFO)

# Connect to database with sqlalchemy.
db = SQLAlchemy(app)

from application.models import *
from application.views import *

class AuthenticatedMenuLink(MenuLink):
	def is_visible(self):
		return session.get('secret')

admin = Admin(app, name='IIF Parser', static_url_path="/assets", template_mode="bootstrap3", 
	index_view=HomeView(name='Secret Key', template='home.html', url='/'))

admin.add_view(Upload(name='Upload/Parse'))
admin.add_link(AuthenticatedMenuLink(name='To IIF File', category='Upload/Parse', url='/upload/iif/'))
admin.add_link(AuthenticatedMenuLink(name='To Quickbooks Online', category='Upload/Parse', url='/upload/quickbooks/'))

admin.add_view(Oauth_Callback(name='Quickbooks Login', endpoint="oauth_callback"))
admin.add_view(RulesView(Rule, db.session, name="Rules"))