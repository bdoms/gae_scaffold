# this is the main entry point for the application
import logging
import os
import sys

from tornado import wsgi

from config import constants
import helpers

# FUTURE: probably move these to requirements
sys.path.append(os.path.join(constants.LIB_PATH, 'python-http-client'))
sys.path.append(os.path.join(constants.LIB_PATH, 'sendgrid-python'))
sys.path.append(os.path.join(constants.LIB_PATH, 'httpagentparser'))
sys.path.append(os.path.join(constants.LIB_PATH, 'gcs', 'python', 'src'))

# logging setup
# TODO: check that these get can be viewed in the logging console in production
access_log = logging.getLogger('tornado.access')
access_log.setLevel(logging.INFO)
application_log = logging.getLogger('tornado.application')
application_log.setLevel(logging.INFO)
general_log = logging.getLogger('tornado.general')
general_log.setLevel(logging.INFO)

# URL routes
from controllers import admin, api, dev, error, home, index, job, sitemap, static, user # NOQA: E204

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

# https://cloud.google.com/appengine/docs/standard/python3/python-differences#modules
app = wsgi.WSGIApplication(handlers=handlers, template_path=constants.VIEWS_PATH, debug=helpers.debug(),
    static_path=constants.STATIC_PATH, cookie_secret=constants.SESSION_KEY, xsrf_cookies=True, login_url='/user/login')

# call this directly to not use dev_appserver.py for local development
if __name__ == "__main__":
    from tornado import ioloop
    level = logging.DEBUG
    access_log.setLevel(level)
    application_log.setLevel(level)
    general_log.setLevel(level)

    port = 8888
    app.listen(port)
    general_log.info('Server running on port ' + str(port))
    ioloop.IOLoop.current().start()
