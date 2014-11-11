from flask.ext.admin import AdminIndexView, expose
from flask import request, session

class HomeView(AdminIndexView):
	@expose('/', methods=["GET","POST"])
	def index(self):
		secret = session.get('secret')
		if request.method == "POST":
			session['secret'] = request.form.get('secret') 
		return self.render('home.html', secret=secret)