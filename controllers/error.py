from controllers.base import BaseController, cacheAndRender
from config.constants import SUPPORT_EMAIL


class ErrorController(BaseController):
    """ handles any page that falls through the rest of config.ROUTES """

    @cacheAndRender()
    def get(self, *args):

        self.renderError(404)


class LogErrorController(BaseController):
    """ called via AJAX to log when static error pages get displayed """

    # called from a static page so it won't know CSRF
    def check_xsrf_cookie(self):
        pass

    def post(self):
        reason = self.request.get('javascript', '')
        if reason:
            exception = JavascriptError(reason)
        else:
            reason = self.request.get('reason', 'None')
            exception = StaticPageError(reason)

        self.logger.error(exception.message)

        self.renderJSON({})

        # send an email notifying us of this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html",
            exception=exception, user=self.user, url=self.request.referer)


class PolicyViolationController(BaseController):
    """ called by the browser to report when a resource violates the CSP """

    # called by the browser so it won't know CSRF
    def check_xsrf_cookie(self):
        pass

    def post(self):
        exception = PolicyViolationError(self.request.body)

        self.logger.error(exception.message)

        self.renderJSON({})

        # send an email notifying us of this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html",
            exception=exception, user=self.user, url=self.request.referer)


class JavascriptError(Exception):
    def __init__(self, reason):
        self.message = 'JavaScript Error: ' + reason


class StaticPageError(Exception):
    def __init__(self, reason):
        self.message = "Static Error Page: " + reason


class PolicyViolationError(Exception):
    def __init__(self, reason):
        self.message = "Content Security Policy Violation: " + reason
