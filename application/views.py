"""
views.py

URL route handlers

Note that any handler params must match the URL route params.
For example the *say_hello* handler, handling the URL route '/hello/<username>',
  must be passed *username* as the argument.

"""
from google.appengine.runtime.apiproxy_errors import CapabilityDisabledError
from flask import request, render_template, url_for, redirect, json, jsonify, Response
from application import app
import csv
import pprint
import re

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
		
	def set_debit_acct(self, value):
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
		self.qb_class = qb_class # by default, splits don't have a class - classes on transactions are ignored without this being filled
		self.amount = split[4]
		try:
			self.memo = split[5]
		except IndexError:
			self.memo = ""
		
	def full_split(self):
		return ['SPL', self.date, self.account, self.name, self.qb_class, self.amount, self.memo]
		
def home():
	ALLOWED_EXTENSIONS = set(['iif'])
	
	def allowed_file(filename):
		return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

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
				elif row[0] == "!SPL":
					headers.append(row)
				elif row[0] == "!ENDTRNS":
					pass # ignore
				else:
					print row
					raise Exception("Unexpected beginning of row. Expecting: TRNS, ENDTRNS, !TRNS, !SPL, !ENDTRNS")
					
			# check header in .iif file to see if it's expected
			expected_header = [['!TRNS', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!SPL', 'DATE', 'ACCNT', 'NAME', 'AMOUNT', 'MEMO']]
			actual_header = [row for row in headers]
			if not (expected_header == actual_header):
				print "Expected: ", expected_header
				print "Actual: ", actual_header
				raise Exception("Expected header did not match actual header.")
				
			unidentified = {}
			considered_dues = [
				'Rose Petefish Payment', 
				'Traditional Monthly Subscription', 
				'Joshua Masseo Payment', 
				'Member Dues', 
				'Membership', 
				'Dallas Makerspace - Invoice', 
				'Transitionary Lock in Rate', 
				'Paul Wilson', 
				'Dallas+Makerspace+-+Invoice+'
			]
			
			# this must be before the FOR loop!
			# add CLASS to !SPL, this prevents quickbooks from ignoring classes on import
			output = [['!TRNS', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO'], ['!SPL', 'DATE', 'ACCNT', 'NAME', 'CLASS', 'AMOUNT', 'MEMO']]
					
			for full_transaction in full_transactions:
				trans = Transaction(full_transaction)
				
				# correct laser consumables transactions 
				if re.match('\d\d\d\d', trans.memo): # pass when it's a 4 digit invoice number
					trans.qb_class = ""
					pass
				elif 'Funds Availability' in trans.qb_class: # exclude these transactions
					trans.ignored = True
				elif trans.memo == "Laser Consumables Fund":
					trans.qb_class = "Laser Cutter Operations Fund"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Laser Cutter Fees")
				elif trans.memo == "Snack Fund":
					trans.qb_class = "Snack Fund"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Snack Sales:Snack Sales Income")
				elif trans.memo == "Machine Shop":
					trans.qb_class = "Machine Shop Committee"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Vinyl Cutter Consumables Fund":
					trans.qb_class = "Screen Printing Operations Fund"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Vinyl Cutter Fees")
				elif trans.memo == "Maker Fellowship Fund":
					trans.qb_class = "Maker Fellowship Fund"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Makerspace General Fund":
					trans.qb_class = ""
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Screen Printing Consumables Fund":
					trans.qb_class = "Screen Printing Operations Fund"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Screen Printing Fees")
				elif trans.memo == "3d Printer Consumables Fund":
					trans.qb_class = "3D Printer Operations Fund"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:3d Printer Fees")
				elif trans.memo == "New Space Build-Out":
					trans.qb_class = "Project - Future Build-Out Fund"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Bridgeport Mill & Accessories":
					trans.qb_class = "Project - Bridgeport Mill"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")	
				elif trans.memo == "TIG Welder":
					trans.qb_class = "Project - TIG Welder"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Mill Simulator":
					trans.qb_class = "Project - Mill Simulator"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")
				elif trans.memo == "Router Table":
					trans.qb_class = "Project - Router Table"
					trans.set_debit_acct("Contributed Support:Revenue from direct contributio:Individual/sm. business contrib")			
				elif trans.memo == "Non DMS Members - Sewing Class":
					trans.qb_class = ""
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees")
				elif trans.memo == "Monthly eBay Seller Fees":
					trans.qb_class = ""
					trans.set_debit_acct("Earned Revenues:Revenue from other sources:Expenses for sales of assets")		
				elif "Express Checkout Payment Received" in trans.qb_class: # classes seem to always be Express Checkout Payment Received
					trans.qb_class = ""
					trans.memo = "Express Checkout Payment Received"
					trans.set_debit_acct("Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees")
				elif trans.memo == "please ignore": # classes seem to always be Express Checkout Payment Received
					trans.qb_class = ""
					trans.memo = ""
					pass	
				elif any(x in trans.memo for x in considered_dues): # pass when it's membership dues
					trans.qb_class = ""
					pass
				else:
					print trans.full_transaction
					# create list with key of missing Class, this is for storing entire unsorted transactions
					if trans.memo not in unidentified.keys():
						unidentified[trans.memo] = []
					unidentified[trans.memo].append(trans.full_transaction) # append unsorted transaction
				
				if not trans.ignored:
					for line in trans.full_transaction:
						output.append(line)
						
			# show problems if there are any unsorted items
			if unidentified:
				outputMessage = "Could not categorize the memo fields (bolded below) of the following items based on existing rules:<br>"
				for unsortedCategory, unsortedList in unidentified.iteritems():
					outputMessage += "<b>" + unsortedCategory + "</b>"
					outputMessage += '<br>'.join(map(str, unsortedList))
				return outputMessage
			else:
				def generate():
					for row in output:
						yield '\t'.join(row) + '\n'
				return Response(generate(), mimetype='text/iif')
	return render_template('home.html')

def warmup():
	"""App Engine warmup handler
	See http://code.google.com/appengine/docs/python/config/appconfig.html#Warming_Requests

	"""
	return ''

