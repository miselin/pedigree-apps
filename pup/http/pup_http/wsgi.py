from google.appengine.api import wrap_wsgi_app

from .views import flask_app

app = wrap_wsgi_app(flask_app.wsgi_app)
