from controllers.base import BaseController

from tornado import web


class HomeController(BaseController):

    @web.authenticated
    def get(self):

        self.renderTemplate('home.html')
