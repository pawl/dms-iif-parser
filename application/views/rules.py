from flask.ext.admin.contrib.sqla import ModelView
from application.models import Rule
from flask import session

class RulesView(ModelView):
	# don't allow access unless the user has entered their secret
	def is_accessible(self):
		return session.get('secret')
		
	def is_visible(self):
		return session.get('secret')
		
	# only show rules with the person's "secret"
	def get_query(self):
		return Rule.query.filter(Rule.secret == session.get('secret'))
		
	# automatically fill "secret" whenever a rule is saved
	def on_model_change(self, form, model, is_created):
		model.secret = session.get('secret')
	
	column_default_sort = "priority"
	column_list = [
		'priority', 
		'match_field',
		'regex_rule',
		'change_debit_class',
		'change_debit_acct',
		'change_memo',
		'ignore'
	]
	form_columns = [
		'priority', 
		'match_field',
		'regex_rule',
		'change_debit_class',
		'debit_class',
		'change_debit_acct',
		'debit_acct',
		'change_memo',
		'memo',
		'ignore'
	]
	column_labels = {
		'match_field': 'Field To Be Matched',
		'regex_rule': 'Match Rule (regex)',
		'change_debit_class': 'Change Debit Class?',
		'debit_class': 'New Debit Class',
		'change_debit_acct': 'Change Debit Account?',
		'debit_acct': 'New Debit Account',
		'change_memo': 'Change Memo Field?',
		'memo': 'New Memo Value',
		'ignore': 'Discard Transaction'
	}
	form_choices = {
		'match_field': [
			('memo', 'memo'), ('qb_class', 'qb_class')
		]
	}