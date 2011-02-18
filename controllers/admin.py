from google.appengine.api import users, memcache
from base import BaseController

LOGOUT_URL = users.create_logout_url("/")


class AdminController(BaseController):
    """ handles request for the admin page """

    def get(self):

        self.renderTemplate('admin/index.html', logout_url=LOGOUT_URL)

    def post(self):

        if self.request.get("memcache"):
            # clear memcache
            memcache.flush_all()

        self.redirect('/admin')

