# this is the main entry point for the application

import webapp2

# URL routes
from controllers import admin, error, index, sitemap, static, tasks

ROUTES = [('/', index.IndexController),
          ('/terms', static.StaticController),
          ('/privacy', static.StaticController),
          ('/sitemap.xml', sitemap.SitemapController),
          ('/admin', admin.AdminController),
          ('/task/sessions', tasks.SessionsController),
          ('/(.*)', error.ErrorController)
         ]

# change debug to False for production
app = webapp2.WSGIApplication(ROUTES, debug=False)
