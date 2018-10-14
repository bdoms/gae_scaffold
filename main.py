# this is the main entry point for the application
import os
import sys

from tornado import wsgi

from config import constants

sys.path.append(os.path.join(constants.LIB_PATH, 'python-http-client'))
sys.path.append(os.path.join(constants.LIB_PATH, 'sendgrid-python'))
sys.path.append(os.path.join(constants.LIB_PATH, 'httpagentparser'))
sys.path.append(os.path.join(constants.LIB_PATH, 'gcs', 'python', 'src')) # should probably be moved to requirements

# URL routes
from controllers import admin, api, dev, error, home, index, job, sitemap, static, user

handlers = [
    ('/', index.IndexController),
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
    ('/job/email', job.EmailController),
    # ('/errors/(.*)', static.StaticController), # uncomment to test static error pages
    ('/logerror', error.LogErrorController),
    ('/policyviolation', error.PolicyViolationController),
    ('/(.*)', error.ErrorController)
]

# TODO: make this env var exists, might have to parse GAE_VERSION instead, see
# https://cloud.google.com/appengine/docs/standard/python3/python-differences
debug = not os.getenv('GAE_ENV', '').startswith('standard')
app = wsgi.WSGIApplication(handlers=handlers, template_path=constants.VIEWS_PATH, debug=debug,
    static_path=constants.STATIC_PATH, cookie_secret=constants.SESSION_KEY,
    xsrf_cookies=True, login_url='/user/login')

# uncomment this to not use dev_appserver.py for testing
# TODO: untested, might have to set some env vars here to match Google
# if __name__ == "__main__":
#     from tornado import ioloop
#     app.listen(8888)
#     tornado.ioloop.IOLoop.current().start()
