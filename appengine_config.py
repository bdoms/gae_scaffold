from datetime import timedelta
from lib.gaesessions import SessionMiddleware

COOKIE_KEY = 'replace this with the output from os.urandom(64)'

def webapp_add_wsgi_middleware(app):
  app = SessionMiddleware(app, cookie_key=COOKIE_KEY, lifetime=timedelta(weeks=2))
  return app

