from controllers.base import BaseController

from tornado import web


class AdminController(BaseController):
    """ handles request for the admin page """

    @web.authenticated
    def before(self):
        if not self.current_user.is_admin:
            return self.renderError(403)

    def get(self):

        self.renderTemplate('admin/index.html')
