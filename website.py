# this is the main entry point for the application

from google.appengine.ext import webapp

from config import ROUTES

def main():
    app = application()
    webapp.util.run_wsgi_app(app)

def application():
    # change debug to False for production
    return webapp.WSGIApplication(ROUTES, debug=True)

if __name__ == "__main__":
    main()

