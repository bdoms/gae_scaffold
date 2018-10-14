from controllers.base import BaseController, withUser


class HomeController(BaseController):

    @withUser
    def get(self):

        self.renderTemplate('home.html')
