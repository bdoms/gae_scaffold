from datetime import datetime

from base import BaseTestCase, UCHAR


# TODO: fill in missing tests
class TestQuery(BaseTestCase):

    def test_fetch(self):
        pass

    def test_get(self):
        pass


class TestBaseModel(BaseTestCase):

    def test_put(self):
        pass

    def test_update(self):
        pass

    def test_create(self):
        pass

    def test_slugToKey(self):
        pass

    def test_getBySlug(self):
        created_user = self.createUser()
        gotten_user = self.model.User.getBySlug(created_user.slug)
        assert gotten_user
        assert created_user.key == gotten_user.key

    def test_properties(self):
        pass

    def test_query(self):
        pass


class TestBooleanProperty(BaseTestCase):

    def test_validate(self):
        pass


class TestDatetimeProperty(BaseTestCase):

    def test_validate(self):
        pass


class TestStringsProperty(BaseTestCase):

    def test_validate(self):
        pass


class TestBytesProperty(BaseTestCase):

    def test_validate(self):
        pass


class TestUser(BaseTestCase):

    def stubUrandom(self, n):
        return b"constant"

    def test_getByEmail(self):
        created_user = self.createUser()
        queried_user = self.model.User.getByEmail(created_user.email)
        assert queried_user
        assert created_user.key == queried_user.key

    def test_hashPassword(self):
        # stub so we get constant results
        orig_pepper = self.model.PASSWORD_PEPPER
        self.model.PASSWORD_PEPPER = b"UxsTc4Et9wtVw+l/D8X+eRoK6jz5z0PTQqKn3pclDZc"

        result = self.model.User.hashPassword("test password" + UCHAR, ("test salt" + UCHAR).encode('utf8'))

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
        self.model.PASSWORD_PEPPER = b"okcPQDpIGZSoky1KexCf0MLKtuUdD6Rr0slwLeqr4UM"

        password_salt, hashed_password = self.model.User.changePassword("test password" + UCHAR)

        # revert the stub to the original now that the method has been called
        self.model.os.urandom = orig_random
        self.model.PASSWORD_PEPPER = orig_pepper

        assert password_salt == b"Y29uc3RhbnQ=" # "constant" base64 encoded

        hsh = "3225aecd07a043a03d92255e03d1cd6e229989f501e6690aaede3ee72d76f39ec"
        hsh += "472778124ec4f4cb153a0954eeebbe6369709149cc2791f3c5c9af57998b71f"
        assert hashed_password == hsh

    def test_getAuth(self):
        pass

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
