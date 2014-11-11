from application import db

class Rule(db.Model):
	__tablename__ = 'rules'
	__table_args__ = (
        db.UniqueConstraint("match_field", "regex_rule"),
    )
	
	id = db.Column(db.Integer, primary_key=True)
	
	match_field = db.Column(db.String(255))
	regex_rule = db.Column(db.String(255))	
	
	#transaction fields being changed, and their new values
	change_debit_class = db.Column(db.Boolean)
	debit_class = db.Column(db.String(255))
	change_debit_acct = db.Column(db.Boolean)
	debit_acct = db.Column(db.String(255))
	change_memo = db.Column(db.Boolean)
	memo = db.Column(db.String(255))
	
	ignore = db.Column(db.Boolean)

	priority = db.Column(db.Integer)
	secret = db.Column(db.String(255))
	
db.create_all()