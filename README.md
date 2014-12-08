dms-iif-parser
============

This project changes IIF files exported from Paypal according to your rules. This is required before Dallas Makerspace imports a paypal export into Quickbooks.
* It can correct the issue with the "CLASS" column being ignored by Quickbooks (the class needs to be added to the first transaction split)
* It can also change the "ACCOUNT" or "MEMO" column based on your rules.

The project is based on the Flask-Bootstrap-Skel template and is built to be used on Heroku.

Credit for Quickbooks Online API login code goes to grue and his django-quickbooks-online project: https://github.com/grue/django-quickbooks-online