from controllers.base import BaseController, withUser


class AdminController(BaseController):
    """ handles request for the admin page """

    @withUser
    def before(self):
        if not self.user.is_admin:
            return self.renderError(403)

    def get(self):

        self.renderTemplate('admin/index.html')
