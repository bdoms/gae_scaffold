# templates
import os

TEMPLATES_DIR = 'templates'
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIR)

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
