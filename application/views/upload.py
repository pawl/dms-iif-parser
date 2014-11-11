import csv
import re

from flask.ext.admin import BaseView, expose
from flask import request, url_for, redirect, Response
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
		
class Upload(BaseView):
	@expose('/', methods=['GET', 'POST'])
	def index(self):		
		def allowed_file(filename):
			# only allow IIF files
			return '.' in filename and filename.rsplit('.', 1)[1] == 'iif'

		if request.method == "POST":
			file = request.files['file']
			if file and allowed_file(file.filename):
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
				new_header = [['!TRNS', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!SPL', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!ENDTRNS']]
				if not (expected_header == actual_header):
					raise Exception("Expected header did not match actual header.")
					
				def change_transaction(trans):
					for rule in Rule.query.all():
						# if any of the rules match, change the transaction
						if re.search(getattr(trans, rule.match_field), rule.regex_rule):
							if rule.change_debit_class:
								trans.debit_class(rule.debit_class)
							if rule.change_debit_acct:
								trans.debit_acct(rule.debit_acct)
							if rule.change_memo:
								trans.memo = rule.memo
							if rule.ignore:
								trans.ignored = rule.ignore
							matched = True
							return trans, matched
					matched = False
					return trans, matched
					
				unmatched_trans = []
				for full_transaction in full_transactions:
					trans = Transaction(full_transaction)
					'''
					if re.search('\d\d\d\d', trans.memo): # no quickbooks class when it's a 4 digit invoice number
						trans.debit_class("")
					elif re.search('Funds Availability', trans.qb_class): # exclude these transactions
						trans.ignored = True
					elif re.search("Laser Consumables Fund", trans.memo):
						trans.debit_class("Laser Cutter Operations Fund")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Laser Cutter Fees")
					elif re.search("Snack Fund", trans.memo):
						trans.debit_class("Snack Fund")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Snack Sales:Snack Sales Income")
					elif re.search("Machine Shop", trans.memo):
						trans.debit_class("Machine Shop Committee")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Vinyl Cutter Consumables Fund", trans.memo):
						trans.debit_class("Screen Printing Operations Fund")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Vinyl Cutter Fees")
					elif re.search("Maker Fellowship Fund", trans.memo):
						trans.debit_class("Maker Fellowship Fund")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Makerspace General Fund", trans.memo):
						trans.debit_class("")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Screen Printing Consumables Fund", trans.memo):
						trans.debit_class("Screen Printing Operations Fund")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Screen Printing Fees")
					elif re.search("3d Printer Consumables Fund", trans.memo):
						trans.debit_class("3D Printer Operations Fund")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:3d Printer Fees")
					elif re.search("New Space Build-Out", trans.memo):
						trans.debit_class("Project - Future Build-Out Fund")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Bridgeport Mill & Accessories", trans.memo):
						trans.debit_class("Project - Bridgeport Mill")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("TIG Welder", trans.memo):
						trans.debit_class("Project - TIG Welder")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Mill Simulator", trans.memo):
						trans.debit_class("Project - Mill Simulator")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Router Table", trans.memo):
						trans.debit_class("Project - Router Table")
						trans.debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
					elif re.search("Non DMS Members - Sewing Class", trans.memo):
						trans.debit_class("")
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees")
					elif re.search("Monthly eBay Seller Fees", trans.memo):
						trans.debit_class("")
						trans.debit_acct("Earned Revenues:Revenue from other sources:Expenses for sales of assets")	
					elif re.search("Express Checkout Payment Received", trans.qb_class): # classes seem to always be Express Checkout Payment Received
						trans.debit_class("")
						trans.memo = "Express Checkout Payment Received"
						trans.debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees")
					elif re.search("please ignore", trans.memo): # override
						trans.debit_class("")
						trans.memo = ""
					elif re.search('Rose Petefish Payment', trans.memo):
						trans.debit_class("")
					elif re.search('Traditional Monthly Subscription', trans.memo):
						trans.debit_class("")
					elif re.search('Joshua Masseo Payment', trans.memo):
						trans.debit_class("")
					elif re.search('Member Dues', trans.memo):
						trans.debit_class("")
					elif re.search('Membership', trans.memo):
						trans.debit_class("")
					elif re.search('Dallas Makerspace - Invoice', trans.memo):
						trans.debit_class("")
					elif re.search('Transitionary Lock in Rate', trans.memo):
						trans.debit_class("")
					elif re.search('Paul Wilson', trans.memo):
						trans.debit_class("")
					elif re.search('Dallas+Makerspace+-+Invoice+', trans.memo):
						trans.debit_class("")
					'''
					trans, matched = change_transaction(trans)
					
					if not matched:						
						unmatched_trans.append(trans) # append unsorted transaction
					
					if not trans.ignored:
						try:
							output += [line for line in trans.full_transaction]
						except UnboundLocalError:
							output = new_header + [line for line in trans.full_transaction]
							
				def generate(output):
					for row in output:
						yield '\t'.join(row) + '\n'
						
				# show problems if there are any unsorted items
				if unmatched_trans:
					output_message = [["Error: Could not categorize the transactions below based on existing rules."]]
					output = output_message + new_header + [row for trans in unmatched_trans for row in trans.full_transaction]
					return Response(generate(output), mimetype='text/iif')
				else:
					return Response(generate(output), mimetype='text/iif')
		return self.render('upload.html')