import logging

from base import BaseController
from config.constants import SUPPORT_EMAIL


class ErrorController(BaseController):
    """ handles any page that falls through the rest of config.ROUTES """

    def get(self, invalid_path):

        self.renderError(404)


class LogErrorController(BaseController):
    """ called via AJAX to log when static error pages get displayed """

    # called from a static page so it won't know CSRF
    SKIP_CSRF = True

    def post(self):
        reason = self.request.get("reason", "None")
        exception = StaticPageError(reason)

        logging.error(exception.message)

        self.renderJSON({})

        # send an email notifying us of this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html",
            exception=exception, user=self.user, url=self.request.referer)


class PolicyViolationController(BaseController):
    """ called by the browser to report when a resource violates the CSP """

    # called by the browser so it won't know CSRF
    SKIP_CSRF = True

    def post(self):
        exception = PolicyViolationError(self.request.body)

        logging.error(exception.message)

        self.renderJSON({})

        # send an email notifying us of this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html",
            exception=exception, user=self.user, url=self.request.referer)


class StaticPageError(Exception):
    def __init__(self, reason):
        self.message = "Static Error Page: " + reason


class PolicyViolationError(Exception):
    def __init__(self, reason):
        self.message = "Content Security Policy Violation: " + reason
