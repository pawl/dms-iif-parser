from flask.ext.admin import AdminIndexView, expose
from flask import request, session, flash

class HomeView(AdminIndexView):
	@expose('/', methods=["GET","POST"])
	def index(self):
		secret = session.get('secret')
		
		if request.method == "POST":
			secret = request.form.get('secret')
			if secret:
				session['secret'] = secret
			else:
				flash("Secret Key cannot be blank.")
				
		return self.render('home.html', secret=secret)