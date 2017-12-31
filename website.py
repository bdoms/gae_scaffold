# this is the main entry point for the application
import os

import webapp2

from config.constants import SESSION_KEY

# URL routes
from controllers import admin, api, dev, error, home, index, job, sitemap, static, user

ROUTES = [('/', index.IndexController),
          ('/home', home.HomeController),
          ('/user', user.IndexController),
          ('/user/auths', user.AuthsController),
          ('/user/email', user.EmailController),
          ('/user/password', user.PasswordController),
          ('/user/signup', user.SignupController),
          ('/user/login', user.LoginController),
          ('/user/logout', user.LogoutController),
          ('/user/forgotpassword', user.ForgotPasswordController),
          ('/user/resetpassword', user.ResetPasswordController),
          ('/terms', static.StaticController),
          ('/privacy', static.StaticController),
          ('/sitemap.xml', sitemap.SitemapController),
          ('/admin', admin.AdminController),
          ('/api/upload', api.UploadController),
          ('/dev', dev.DevController),
          ('/job/auths', job.AuthsController),
          #('/errors/(.*)', static.StaticController), # uncomment to test static error pages
          ('/logerror', error.LogErrorController),
          ('/policyviolation', error.PolicyViolationController),
          ('/(.*)', error.ErrorController)
         ]

# any extra config needed when the app starts
cookie_args = {
    # this can prevent XSS attacks by not letting javascript access the cookie
    # (note that some older browsers do not have this restriction implemented)
    # disable if you need to access cookies from javascript (not recommended)
    'httponly': True
}

if not os.environ.get('SERVER_SOFTWARE', '').startswith('Development'):
    # force cookies to only be sent over SSL
    cookie_args['secure'] = True

config = {'webapp2_extras.sessions': {
    'secret_key': SESSION_KEY,
    'cookie_args': cookie_args
}}

# make sure debug is False for production
app = webapp2.WSGIApplication(ROUTES, config=config, debug=False)
