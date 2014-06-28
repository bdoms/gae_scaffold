from google.appengine.api import users, memcache
from base import BaseController

import model

LOGOUT_URL = users.create_logout_url("/")


class DevController(BaseController):
    """ handles request for the dev page """

    def get(self):

        self.renderTemplate('dev.html', logout_url=LOGOUT_URL)

    def post(self):

        if self.request.get("make_admin"):
            email = self.request.get("email")
            user = model.User.query(model.User.email == email).get()
            if user:
                user.is_admin = True
                user.put()
            else:
                # TODO: flash a message about the user not existing here
                pass
        elif self.request.get("memcache"):
            # clear memcache
            memcache.flush_all()

        self.redirect('/dev')
