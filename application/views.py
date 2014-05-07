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

def home():
	ALLOWED_EXTENSIONS = set(['iif'])
	
	def allowed_file(filename):
		return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

	if request.method == "POST":
		file = request.files['file']
		if file and allowed_file(file.filename):
			reader = csv.reader(file,delimiter='\t')
			allTransactions = []
			transaction = []
			# read IIF file and add each transaction to a list
			headers = []
			for x in reader:
				if x[0] == "TRNS":
					transaction = []
					transaction.append(x)
				elif x[0] == "ENDTRNS":
					transaction.append(x)
					allTransactions.append(transaction)
				elif x[0] == "!TRNS": 
					headers.append(x)
				elif x[0] == "!SPL":
					x.insert(4,'CLASS')
					headers.append(x)
				else:
					transaction.append(x)
			dictOfUnsorted = {}
			p = re.compile('\d\d\d\d')
			listOfDues = ["Rose Petefish Payment", "Traditional Monthly Subscription", "Joshua Masseo Payment", "Member Dues", "Membership", "Dallas Makerspace - Invoice", 'Transitionary Lock in Rate', 'Paul Wilson', 'Dallas+Makerspace+-+Invoice+']
			
			output = []
			for x in headers:
				output.append(x) # file header for IIF
				
			for transaction in allTransactions:
				# correct laser consumables transactions 
				addToArray = True
				if p.match(transaction[0][6]): # pass when it's a 4 digit invoice number
					transaction[0][4] = ""
					pass
				elif 'Funds Availability' in transaction[0][4]: # exclude these transactions
					addToArray = False
				elif transaction[0][6] == "Laser Consumables Fund":
					transaction[0][4] = "Laser Cutter Operations Fund"
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:Laser Cutter Fees"
				elif transaction[0][6] == "Snack Fund":
					transaction[0][4] = "Snack Fund"
					transaction[1][2] = "Earned Revenues:Revenue from other sources:Misc revenue:Snacks Income"
				elif transaction[0][6] == "Vinyl Cutter Consumables Fund":
					transaction[0][4] = "Screen Printing Operations Fund"
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:Vinyl Cutter Fees"
				elif transaction[0][6] == "Maker Fellowship Fund":
					transaction[0][4] = "Maker Fellowship Fund"
					transaction[1][2] = "Contributed Support:Revenue from direct contributio:Individual/sm. business contrib"
				elif transaction[0][6] == "Makerspace General Fund":
					transaction[0][4] = ""
					transaction[1][2] = "Contributed Support:Revenue from direct contributio:Individual/sm. business contrib"
				elif transaction[0][6] == "Screen Printing Consumables Fund":
					transaction[0][4] = "Screen Printing Operations Fund"
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:Screen Printing Fees"
				elif transaction[0][6] == "3d Printer Consumables Fund":
					transaction[0][4] = "3D Printer Operations Fund"
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:3d Printer Fees"
				elif transaction[0][6] == "Non DMS Members - Sewing Class":
					transaction[0][4] = ""
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees"
				elif transaction[0][6] == "Monthly eBay Seller Fees":
					transaction[0][4] = ""
					transaction[1][2] = "Earned Revenues:Revenue from other sources:Expenses for sales of assets"					
				elif "Express Checkout Payment Received" in transaction[0][4]: # classes seem to always be Express Checkout Payment Received
					transaction[0][4] = ""
					transaction[0][6] = "Express Checkout Payment Received"
					transaction[1][2] = "Earned Revenues:Revenue from program-related sa:Program service fees:Class Fees"	
				elif any(x in transaction[0][6] for x in listOfDues): # pass when it's membership dues
					transaction[0][4] = ""
					pass
				else:
					print transaction
					# create list with key of missing Class, this is for storing entire unsorted transactions
					if transaction[0][6] not in dictOfUnsorted.keys():
						dictOfUnsorted[transaction[0][6]] = []
					dictOfUnsorted[transaction[0][6]].append(transaction) # append unsorted transaction
				#if transaction[0][6]:
				#	transaction[0][6] = '"' + transaction[0][6] + '"' # fix errors due to lack of escaping
				for i in range(1,len(transaction)):
					if i == 1:
						transaction[i].insert(4,transaction[0][4]) # add new class to 1st split
					else:
						transaction[i].insert(4,"")
				if addToArray:
					for x in transaction:
						output.append(x)
						
			# show problems if there are any unsorted items
			if dictOfUnsorted:
				outputMessage = "Could not categorize the Classes (bolded below) of the following items based on existing rules:<br>"
				for unsortedCategory, unsortedList in dictOfUnsorted.iteritems():
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

