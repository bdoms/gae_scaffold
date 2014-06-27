
import base64
import pickle
import unittest

from google.appengine.ext import testbed
from google.appengine.datastore import datastore_stub_util

from config.constants import CURRENT_DIR


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
