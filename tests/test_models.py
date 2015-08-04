
import datetime

from base import BaseTestCase, UCHAR


class TestUser(BaseTestCase):

    def test_getByEmail(self):
        created_user = self.createUser()
        queried_user = self.model.User.getByEmail(created_user.email)
        assert created_user.key == queried_user.key

    def test_hashPassword(self):
        result = self.model.User.hashPassword("test password" + UCHAR, "test salt" + UCHAR)
        assert result == "38051ae4e79c5f5b59fead47300c56d3b6d3a90b050a338f75cd8e637e1dac6f7968473fab0f6870841c9e6dc166fd7f7d9b7fb839f4dfeb2e8c76f82c7c6033"

    def test_changePassword(self):
        # stub the os urandom method so that we get constant results
        def stubUrandom(n):
            return "constant"
        orig = self.model.os.urandom
        self.model.os.urandom = stubUrandom

        password_salt, hashed_password = self.model.User.changePassword("test password" + UCHAR)

        # revert the stub to the original now that the method has been called
        self.model.os.urandom = orig

        assert password_salt == "Y29uc3RhbnQ=\n" # "constant" base64 encoded
        assert hashed_password == "5e42e48a883c89d4975342bfcbb43732dbac170814a73de2ef9d795e1551699129e9faade7b347bd1b3473a7179db03886dde8f27b7c6418de75e5d6a0bd20c2"

    def test_resetPasswordToken(self):
        user = self.createUser()
        user.hashed_password = "test hash"
        dt = datetime.datetime(2000, 1, 1)
        result = user.resetPasswordToken(timestamp=dt)
        assert result == "5324d910f13981f6600135288ff4c9899c90b8e4ffddefcbc172d1e275558489965f005a448041ed94842c7c2b62dab6c62832c5c3088d05477ec83a123d44a9"


class TestModelFunctions(BaseTestCase):

    def test_getByKey(self):
        created_user = self.createUser()
        gotten_user = self.model.getByKey(created_user.key.urlsafe())
        assert created_user.key == gotten_user.key

    def test_cache(self):
        self.executed = 0
        def testFunction():
            self.executed += 1
            return "test value"
        assert self.executed == 0

        result = self.model.cache("test key", testFunction)
        assert result == "test value"
        assert self.executed == 1

        # the value should now be cached, so the function should not be executed again
        result = self.model.cache("test key", testFunction)
        assert self.executed == 1
