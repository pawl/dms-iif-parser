# Credit to grue's django-quickbooks-online: https://github.com/grue/django-quickbooks-online

from requests_oauthlib import OAuth1Session
from flask.ext.admin import BaseView, expose
from flask import session, flash, request, redirect
from application import app

class QuickbooksToken:
    def __init__(self, access_token, access_token_secret, realm_id):
        access_token = access_token
        access_token_secret = access_token_secret
        realm_id = realm_id

class Oauth_Callback(BaseView):
    def is_visible(self):
        return False
    
    @expose('/', methods=['GET', 'POST'])
    def index(self, output_type=None):
        # gets access token
        ACCESS_TOKEN_URL = 'https://oauth.intuit.com/oauth/v1/get_access_token'
        
        qb_session = OAuth1Session(client_key=app.config['QB_KEY'],
                                   client_secret=app.config['QB_SECRET'],
                                   resource_owner_key=session['qb_oauth_token'],
                                   resource_owner_secret=session['qb_oauth_token_secret'])

        remote_response = qb_session.parse_authorization_response(request.url)
        realm_id = request.args.get('realmId')
        data_source = request.args.get('dataSource')
        oauth_verifier = request.args.get('oauth_verifier')

        # [review] - Possible bug? This should be taken care of by qb_session.parse_authorization_response
        qb_session.auth.client.verifier = unicode(oauth_verifier)

        response = qb_session.fetch_access_token(ACCESS_TOKEN_URL)

        session['access_token'] = response['oauth_token']
        session['access_token_secret'] = response['oauth_token_secret']
        session['realm_id'] = realm_id
        session['data_source'] = data_source
            
        return redirect('/upload/quickbooks')