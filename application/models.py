from google.appengine.ext import ndb

class ReplacementDataModel(ndb.Model):
    original_class = ndb.StringProperty(required=True)
    line1_class = ndb.TextProperty() # this replaces the class on the TRNS line
	line2_account = ndb.TextProperty() # this replaces the account on the 1st split line