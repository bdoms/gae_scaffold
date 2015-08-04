import logging

from base import BaseController


class ErrorController(BaseController):
    """ handles any page that falls through the rest of config.ROUTES """

    def get(self, invalid_path):

        self.renderError(404)


class LogErrorController(BaseController):
    """ called via AJAX to log when static error pages get displayed """

    def post(self):
        reason = self.request.get("reason", "None")
        exception = StaticPageError(reason)

        logging.error(exception.message)

        self.renderJSON({})


class StaticPageError(Exception):
    def __init__(self, reason):
        self.message = "Static Error Page: " + reason
