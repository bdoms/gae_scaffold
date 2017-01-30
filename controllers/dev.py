from google.appengine.api import users, memcache
from base import FormController

import model

from gae_validators import validateEmail

LOGOUT_URL = users.create_logout_url("/")


class DevController(FormController):
    """ handles request for the dev page """

    FIELDS = {"email": validateEmail}

    def get(self):

        self.renderTemplate('dev.html', logout_url=LOGOUT_URL)

    def post(self):

        if self.request.get("make_admin"):
            form_data, errors, valid_data = self.validate()
            if not errors:
                user = model.User.query(model.User.email == valid_data["email"]).get()
                if user:
                    user.is_admin = True
                    user.put()

                    # the user may currently be signed in so invalidate its cache to get the new permissions
                    self.uncache(user.key.urlsafe())
                    self.flash("success", "User successfully made admin.")
                else:
                    errors["exists"] = True
            if errors:
                return self.redisplay(form_data, errors)

        elif self.request.get("memcache"):
            # clear memcache
            memcache.flush_all()

        self.redisplay()
