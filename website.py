# this is the main entry point for the application

import webapp2

# URL routes
from controllers import admin, dev, error, home, index, sitemap, static, user

ROUTES = [('/', index.IndexController),
          ('/home', home.HomeController),
          ('/signup', user.SignupController),
          ('/login', user.LoginController),
          ('/logout', user.LogoutController),
          ('/terms', static.StaticController),
          ('/privacy', static.StaticController),
          ('/sitemap.xml', sitemap.SitemapController),
          ('/admin', admin.AdminController),
          ('/dev', dev.DevController),
          ('/(.*)', error.ErrorController)
         ]

# any extra config needed when the app starts
config = {}
config['webapp2_extras.sessions'] = {
    'secret_key': 'replace this with the output from os.urandom(64)',
    'cookie_args': {
        # uncomment this line to force cookies to only be sent over SSL
        #'secure': True,

        # this can prevent XSS attacks by not letting javascript access the cookie
        # (note that some older browsers do not have this restriction implemented)
        # disable if you need to access cookies from javascript (not recommended)
        'httponly': True
    }
}

# make sure debug is False for production
app = webapp2.WSGIApplication(ROUTES, config=config, debug=False)
