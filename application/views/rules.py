from flask.ext.admin.contrib.sqla import ModelView
from application.models import Rule
from flask import session

class RulesView(ModelView):
	column_default_sort = "priority"
	
	def get_query(self):
		return Rule.query.filter(Rule.secret == session['secret'])
		
	def on_model_change(self, form, model, is_created):
		model.secret = session['secret']