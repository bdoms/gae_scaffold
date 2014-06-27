# this is the main entry point for the application

import webapp2

# URL routes
from controllers import admin, error, index, sitemap, static

ROUTES = [('/', index.IndexController),
          ('/terms', static.StaticController),
          ('/privacy', static.StaticController),
          ('/sitemap.xml', sitemap.SitemapController),
          ('/admin', admin.AdminController),
          ('/(.*)', error.ErrorController)
         ]

# any extra config needed when the app starts
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'replace this with the output from os.urandom(64)',
}

# make sure debug is False for production
app = webapp2.WSGIApplication(ROUTES, config=config, debug=False)
