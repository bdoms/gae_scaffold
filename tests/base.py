
import base64
import os
import pickle
import unittest

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

from config.constants import CURRENT_DIR

import model

UCHAR = u"\u03B4" # lowercase delta


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        # First, create an instance of the Testbed class.
        self.testbed = testbed.Testbed()
        # Then activate the testbed, which prepares the service stubs for use.
        self.testbed.activate()
        # Create a consistency policy that will simulate the High Replication consistency model.
        self.policy = datastore_stub_util.PseudoRandomHRConsistencyPolicy(probability=0)
        # Next, declare which service stubs you want to use.
        self.testbed.init_blobstore_stub()
        self.testbed.init_datastore_v3_stub()
        self.testbed.init_memcache_stub()
        self.testbed.init_user_stub()
        # need to include the path where queue.yaml exists so that the stub knows about named queues
        self.testbed.init_taskqueue_stub(root_path=CURRENT_DIR)
        self.task_stub = self.testbed.get_stub(testbed.TASKQUEUE_SERVICE_NAME)
        self.testbed.init_mail_stub()
        self.mail_stub = self.testbed.get_stub(testbed.MAIL_SERVICE_NAME)

    def tearDown(self):
        self.testbed.deactivate()

    def executeDeferred(self, name="default"):
        # see http://stackoverflow.com/questions/6632809/gae-unit-testing-taskqueue-with-testbed
        tasks = self.task_stub.GetTasks(name)
        self.task_stub.FlushQueue(name)
        while tasks:
            for task in tasks:
                (func, args, opts) = pickle.loads(base64.b64decode(task["body"]))
                func(*args)
            tasks = self.task_stub.GetTasks(name)
            self.task_stub.FlushQueue(name)

        # Run each of the tasks, checking that they succeeded.
        for task in tasks:
            response = self.post(task['url'], task['params'])
            self.assertOK(response)

    # fixtures
    def createUser(self, email=None, is_admin=False, **kwargs):
        first_name = "Test first name" + UCHAR
        last_name = "Test last name" + UCHAR
        email = email or "test" + UCHAR + "@example.com"
        password = "Test password" + UCHAR

        password_salt = os.urandom(64).encode("base64")
        hashed_password = model.User.hashPassword(password, password_salt)
        other_user = model.User.query(model.User.email == email).get()
        assert not other_user, "That email address is already in use."
        user = model.User(first_name=first_name, last_name=last_name, email=email,
            password_salt=password_salt, hashed_password=hashed_password, is_admin=is_admin, **kwargs)
        user.put()
        user.password = password # for convenience with signing in during testing

        if email == "test" + UCHAR + "@example.com":
            # this is the default, so add an easy reference to it
            self.user = user

        return user
