import os

from lib import gae_html
from lib.gae_validators import validateEmail

from controllers.base import FormController
import helpers
import model

SERVICE = os.getenv('GAE_SERVICE', '')
VERSION = os.getenv('GAE_VERSION', '')


class DevController(FormController):
    """ handles request for the dev page """

    FIELDS = {"email": validateEmail}

    def before(self):
        if (not self.current_user or not self.current_user.is_dev) and not helpers.debug():
            return self.renderError(403)

    def get(self):
        self.renderTemplate('dev.html', service=SERVICE, version=VERSION)

    def post(self):

        if self.get_argument('clear_cache', None):
            helpers.clear_cache()
            gae_html.clearCache()
            self.logger.info('Cleared cache.')
            self.flash("info", "Cache Cleared")

        elif self.get_argument('make_admin', None):
            form_data, errors, valid_data = self.validate()
            if not errors:
                user = model.User.getByEmail(valid_data["email"])
                if user:
                    user.update(is_admin=True)
                    user.put()

                    # the user may currently be signed in so invalidate its cache to get the new permissions
                    helpers.uncache(user.slug)
                    self.logger.info('Made user admin: ' + valid_data['email'])
                    self.flash("success", "User successfully made admin.")
                else:
                    errors["exists"] = True
            if errors:
                return self.redisplay(form_data, errors)

        elif self.get_argument('migrate', None):
            self.logger.info('Beginning migration.')
            modified = []

            # do migration work
            # q = model.User.query()
            # for entity in q.fetch():
            #     entity = model.User.updateEntity(entity, {'prop': 'value'})
            #     modified.append(entity)

            if modified:
                model.db.put_multi(modified)

            self.logger.info('Migration finished. Modified ' + str(len(modified)) + ' items.')
            self.flash('success', 'Migrations Complete')

        elif self.get_argument('reset', None) and helpers.debug():
            # delete all entities for all classes
            model_classes = [model.Auth, model.User]
            for model_class in model_classes:
                q = model_class.query()
                q.keys_only()
                entities = list(q.fetch())
                if len(entities) > 0:
                    # note that keys_only still returns the whole entity
                    model.db.delete_multi([entity.key for entity in entities])

            # add any fixtures needed for development here
            password_salt, hashed_password = model.User.changePassword('test')
            user = model.User.create(first_name='Test', last_name='Testerson', email='test@test.com',
                password_salt=password_salt, hashed_password=hashed_password)
            user.put()

            # auto signout since the IDs and keys have all changed
            self.clear_all_cookies()
            helpers.clear_cache()
            self.flash('info', 'Data Reset')

        self.redisplay()
