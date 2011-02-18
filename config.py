# templates
import os

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_PATH = os.path.join(CURRENT_DIR, 'templates')
LIB_PATH = os.path.join(CURRENT_DIR, 'lib')

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
