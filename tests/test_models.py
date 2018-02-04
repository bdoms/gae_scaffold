from datetime import datetime

from base import BaseTestCase, UCHAR


class TestUser(BaseTestCase):

    def stubUrandom(self, n):
        return "constant"

    def test_getByEmail(self):
        created_user = self.createUser()
        queried_user = self.model.User.getByEmail(created_user.email)
        assert created_user.key == queried_user.key

    def test_hashPassword(self):
        # stub so we get constant results
        orig_pepper = self.model.PASSWORD_PEPPER
        self.model.PASSWORD_PEPPER = "UxsTc4Et9wtVw+l/D8X+eRoK6jz5z0PTQqKn3pclDZc"

        result = self.model.User.hashPassword("test password" + UCHAR, "test salt" + UCHAR)

        # revert the stub
        self.model.PASSWORD_PEPPER = orig_pepper

        hsh = "91a97a3db1c2b744579e5d961c85501342f99fe3e2e27641a794455f85607130"
        hsh += "1809d9c273738df490d3933fd087a8fbe1d8833d519ee6dc0f12c0005040b40e"
        assert result == hsh

    def test_changePassword(self):
        # stub so we get constant results
        orig_random = self.model.os.urandom
        orig_pepper = self.model.PASSWORD_PEPPER
        self.model.os.urandom = self.stubUrandom
        self.model.PASSWORD_PEPPER = "okcPQDpIGZSoky1KexCf0MLKtuUdD6Rr0slwLeqr4UM"

        password_salt, hashed_password = self.model.User.changePassword("test password" + UCHAR)

        # revert the stub to the original now that the method has been called
        self.model.os.urandom = orig_random
        self.model.PASSWORD_PEPPER = orig_pepper

        assert password_salt == "Y29uc3RhbnQ=\n" # "constant" base64 encoded

        hsh = "a3aefba6defa1b49bcbcfb65e5be16976e91be9c5e5d258782abf35480c52a77"
        hsh += "0a6ef5b80f7c53c20e624d4e9f2279ab2693a0f3278cffd1481b6a1252bbe0dc"
        assert hashed_password == hsh

    def test_resetPassword(self):
        user = self.createUser()

        # stub the os urandom method so that we get constant results
        orig = self.model.os.urandom
        self.model.os.urandom = self.stubUrandom

        user = user.resetPassword()

        # revert the stub to the original now that the method has been called
        self.model.os.urandom = orig

        assert user.token == "Y29uc3RhbnQ" # "constant" base64 encoded for URLs
        assert (datetime.utcnow() - user.token_date).total_seconds() < 1 # should be very fresh


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
        assert result == "test value"
        assert self.executed == 1

    def test_uncache(self):
        self.executed = 0

        def testFunction():
            self.executed += 1
            return True

        assert self.executed == 0

        result = self.model.cache("test key", testFunction)
        assert result is True
        assert self.executed == 1

        self.model.uncache("test key")

        # the value should not be cached, so the function should execute again
        result = self.model.cache("test key", testFunction)
        assert result is True
        assert self.executed == 2
