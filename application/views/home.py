from flask.ext.admin import AdminIndexView, expose
from flask import request, session, flash, redirect, url_for

class HomeView(AdminIndexView):
	@expose('/', methods=["GET","POST"])
	def index(self):
		secret = session.get('secret')
		
		if request.method == "POST":
			secret = request.form.get('secret')
			if secret:
				session['secret'] = secret
				return redirect(url_for('upload.index'))
			else:
				flash("Secret Key cannot be blank.")
				
		return self.render('home.html', secret=secret)