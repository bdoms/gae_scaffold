import logging

#from google.appengine.api import users, memcache
#from google.appengine.api.namespace_manager import namespace_manager

from controllers.base import FormController
import helpers
import model

from lib.gae_validators import validateEmail

#LOGOUT_URL = users.create_logout_url("/")
#NAMESPACE = namespace_manager.get_namespace()


class DevController(FormController):
    """ handles request for the dev page """

    FIELDS = {"email": validateEmail}

    def get(self):

        self.renderTemplate('dev.html', namespace='', logout_url='')

    def post(self):

        if self.get_argument('make_admin'):
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

        elif self.get_argument('memcache'):
            # clear memcache
            memcache.flush_all()
            self.flash('info', 'Cleared Memcache')

        elif self.get_argument('migrate'):
            logging.info('Beginning migration.')
            modified = []

            # do migration work
            # q = model.User.query()
            # for item in q:
            #     modified.append(item)

            if modified:
                model.ndb.put_multi(modified)

            logging.info('Migration finished. Modified ' + str(len(modified)) + ' items.')
            self.flash('success', 'Migrations Complete')

        elif self.get_argument('reset') and helpers.debug():
            # delete all entities for all classes
            model_classes = [model.Auth, model.User]
            for model_class in model_classes:
                entities = model_class.query().fetch(keys_only=True)
                if len(entities) > 0:
                    model.ndb.delete_multi(entities)

            # add any fixtures needed for development here
            password_salt, hashed_password = model.User.changePassword('test')
            user = model.User(first_name='Test', last_name='Testerson', email='test@test.com',
                password_salt=password_salt, hashed_password=hashed_password)
            user.put()

            # auto signout since the IDs and keys have all changed
            self.session.clear()
            self.flash('info', 'Data Reset')

        self.redisplay()
