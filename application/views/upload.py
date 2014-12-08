import csv
import re
import urllib

from requests_oauthlib import OAuth1Session
from flask.ext.admin import BaseView, expose
from flask import request, url_for, redirect, Response, session, flash
from application import app, db
from application.models import Rule

# a paypal transaction from a .iif export, includes SPL lines
class Transaction:
    def __init__(self, full_transaction):
        if full_transaction[0][0] != "TRNS":
            raise Exception("Not a valid transaction. Expecting a line starting with TRNS.")
            
        self.date = full_transaction[0][1]
        self.account = full_transaction[0][2] # decreases (because it's an asset account)
        self.name = full_transaction[0][3]
        self.qb_class = full_transaction[0][4] # in DMS's situation, we don't use classes on asset accounts, so this is applied to the split transaction
        self.amount = full_transaction[0][5]
        self.memo = full_transaction[0][6]
        
        self.ignored = False
        
        # build list of splits, everything but the first line of the transaction is a split
        self.splits = []
        for split_count in xrange(1,len(full_transaction)):
            self.splits.append(Split(full_transaction[split_count], self.qb_class))            
    
    def debit_class(self, value):
        self.splits[0].qb_class = value
        self.qb_class = value
        
    def debit_acct(self, value):
        self.splits[0].account = value
        
    # returns the list needed for final output
    @property
    def full_transaction(self):
        trans = [['TRNS', self.date, self.account, self.name, self.qb_class, self.amount, self.memo]]
        for split in self.splits:
            trans.append(split.full_split())
        trans.append(['ENDTRNS'])
        return trans
        
# contained by a Transaction
class Split:
    def __init__(self, split, qb_class):
        if split[0] != "SPL":
            print split
            raise Exception("Not a valid split for a transaction. Expecting a line starting with SPL after line starting with TRNS.")
            
        self.date = split[1]
        self.account = split[2]
        self.name = split[3]
        self.qb_class = "" # by default, splits don't have a class - classes on transactions are ignored without this being filled
        self.amount = split[4]
        try:
            self.memo = split[5]
        except IndexError:
            self.memo = ""
        
    def full_split(self):
        return ['SPL', self.date, self.account, self.name, self.qb_class, self.amount, self.memo]
        
def iif_to_trans_class(file):
    reader = csv.reader(file, delimiter='\t')
                
    # read IIF file and add each transaction to a list
    full_transactions = []
    for row in reader:
        if row[0] == "TRNS":
            transaction = [row]
        elif row[0] == "SPL":
            transaction.append(row)
        elif row[0] == "ENDTRNS":
            full_transactions.append(transaction)
        elif row[0] == "!TRNS": # only headers start with !
            headers = [row]
        elif row[0] in ["!SPL", "!ENDTRNS"]:
            headers.append(row)
        else:
            print row
            raise Exception("Unexpected beginning of row. Expecting: TRNS, ENDTRNS, !TRNS, !SPL, !ENDTRNS")
            
    # check header in .iif file to see if it's expected
    expected_header = [['!TRNS', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!SPL', 'DATE', 'ACCNT', 'NAME', 'AMOUNT', 'MEMO'], ['!ENDTRNS']]
    actual_header = [row for row in headers]
    if expected_header != actual_header:
        raise Exception("Expected header did not match actual header.")
        
    def change_transaction(trans):
        for rule in Rule.query.filter(Rule.secret == session.get('secret')):
            # if any of the rules match, change the transaction
            if re.search(rule.regex_rule, getattr(trans, rule.match_field)):
                if rule.change_debit_class:
                    trans.debit_class((rule.debit_class or ""))
                if rule.change_debit_acct:
                    trans.debit_acct((rule.debit_acct or ""))
                if rule.change_memo:
                    trans.memo = (rule.memo or "")
                if rule.ignore:
                    trans.ignored = rule.ignore
                return trans, True # matched = True
        return trans, False # matched = False
        
    unmatched_trans = []
    matched_trans = []
    for full_transaction in full_transactions:
        trans = Transaction(full_transaction)

        trans, matched = change_transaction(trans)                    
        if not matched:                
            unmatched_trans.append(trans) # append unsorted transaction
            
        if not trans.ignored:
            matched_trans.append(trans) # append unsorted transaction
        
    return matched_trans, unmatched_trans

def allowed_file(filename):
    # only allow IIF files
    return '.' in filename and filename.rsplit('.', 1)[1] == 'iif'

def generate(output):
    for row in output:
        yield '\t'.join(row) + '\n'
                    
class Upload(BaseView):
    # don't allow access unless the user has entered their secret
    def is_accessible(self):
        return session.get('secret')
        
    def is_visible(self):
        return False
    
    # can't return redirect in is_accessible or it will cause errors
    def _handle_view(self, name, **kwargs):
        if not self.is_accessible():
            flash('Secret key required.')
            return redirect('/')
    
    @expose('/', methods=['GET', 'POST'])
    @expose('/<output_type>/', methods=['GET', 'POST'])
    def index(self, output_type=None):        
        if request.method == "POST":
            file = request.files['file']
            if file and allowed_file(file.filename):
                new_header = [['!TRNS', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!SPL', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!ENDTRNS']]
                
                matched_trans, unmatched_trans = iif_to_trans_class(file)
                        
                # show problems if there are any unsorted items
                if unmatched_trans:
                    output_message = [["Error: Could not categorize the transactions below based on existing rules."]]
                    output = output_message + new_header + [row for trans in unmatched_trans for row in trans.full_transaction]
                    return Response(generate(output), mimetype='text/iif')
                else:
                    if output_type == "quickbooks":
                        # QBO login credit to grue's django-quickbooks-online.
                        # Project URL: https://github.com/grue/django-quickbooks-online
                        if not session['access_token'] and session['access_token_secret'] and session['realm_id']:
                            REQUEST_TOKEN_URL = 'https://oauth.intuit.com/oauth/v1/get_request_token'
                            AUTHORIZATION_URL = 'https://appcenter.intuit.com/Connect/Begin'
                            
                            qb_session = OAuth1Session(client_key=app.config['QB_KEY'],
                                                    client_secret=app.config['QB_SECRET'],
                                                    callback_uri=app.config['QB_CALLBACK_URL'])

                            response = qb_session.fetch_request_token(REQUEST_TOKEN_URL)

                            request_token = response['oauth_token']
                            request_token_secret = response['oauth_token_secret']

                            session['qb_oauth_token'] = request_token
                            session['qb_oauth_token_secret'] = request_token_secret
                            
                            return redirect("%s?oauth_token=%s" % (AUTHORIZATION_URL, request_token))
                        else:
                            qb_session = OAuth1Session(client_key=app.config['QB_KEY'],
                                                       client_secret=app.config['QB_SECRET'],
                                                       resource_owner_key=session['access_token'],
                                                       resource_owner_secret=session['access_token_secret'])

                            qb_session.headers.update({'content-type': 'application/json', 'accept': 'application/json'})
                            realm_id = session['realm_id']
                            data_source = session['data_source']
                            
                            #url_base = 'https://quickbooks.api.intuit.com/v3'
                            url_base = 'https://sandbox-quickbooks.api.intuit.com/v3/'
                            
                            # create list of accounts
                            accounts = {}
                            constructed_url = "{}/company/{}/query?query={}".format(url_base, realm_id, urllib.quote('Select * From Account'))
                            for account in qb_session.get(constructed_url).json()['QueryResponse']['Account']:
                                accounts[account['Id']] = account['FullyQualifiedName']
                            
                            '''
                            # create transactions
                            constructed_url = "{}/company/{}/{}".format(url_base, realm_id, object_type)
                            for trans in matched_trans:
                                if not trans.ignored:
                                    qb_session.post(constructed_url.lower(), object_body).json()
                            '''
                            
                            flash('Upload to quickbooks successful.')
                            return redirect('/upload/quickbooks')
                        
                    elif output_type == "iif":
                        for trans in matched_trans:
                            if not trans.ignored:
                                try:
                                    output += [line for line in trans.full_transaction]
                                except UnboundLocalError:
                                    output = new_header + [line for line in trans.full_transaction]
                    else:
                        raise Exception("Unexpected Output Type")
                    return Response(generate(output), mimetype='text/iif')
        return self.render('upload.html')