import base64
import unittest
import urllib.request

from config.constants import DATASTORE_EMULATOR_HOST

UCHAR = u"\u03B4" # lowercase delta


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # TODO: stub for testing mail

        # need to post to the emulator to reset old data
        # https://stackoverflow.com/questions/46956758/google-datastore-emulator-remove-data-from-local-database'
        urllib.request.urlopen('http://' + DATASTORE_EMULATOR_HOST + '/reset', {})

        import model
        self.model = model

        import helpers
        helpers.clear_cache()

    def executeDeferred(self, name="default"):
        # see http://stackoverflow.com/questions/6632809/gae-unit-testing-taskqueue-with-testbed
        tasks = self.task_stub.GetTasks(name)
        self.task_stub.FlushQueue(name)

        while tasks:
            # run each of the tasks, checking that they succeeded
            for task in tasks:
                params = base64.b64decode(task['body'])
                assert self.app.post(task['url'], params)

            # running tasks can add more tasks, so keep checking until there's none
            tasks = self.task_stub.GetTasks(name)
            self.task_stub.FlushQueue(name)

    # fixtures
    def createUser(self, email=None, is_admin=False, **kwargs):
        first_name = "Test first name" + UCHAR
        last_name = "Test last name" + UCHAR
        email = email or "test" + UCHAR + "@example.com"
        password = "Test password" + UCHAR

        other_user = self.model.User.getByEmail(email)
        assert not other_user, "That email address is already in use."

        password_salt, hashed_password = self.model.User.changePassword(password)
        user = self.model.User.create(first_name=first_name, last_name=last_name, email=email,
            password_salt=password_salt, hashed_password=hashed_password, is_admin=is_admin, **kwargs)
        user.put()
        user.password = password # for convenience with signing in during testing

        if email == "test" + UCHAR + "@example.com":
            # this is the default, so add an easy reference to it
            self.user = user

        return user

    def createAuth(self, user):
        auth = self.model.Auth.create(user_agent='test user agent' + UCHAR, os='test os' + UCHAR,
            browser='test browser' + UCHAR, device='test device' + UCHAR, ip='127.0.0.1', parent=user.key)
        auth.put()
        return auth
