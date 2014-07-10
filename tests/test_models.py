
from base import BaseTestCase, UCHAR

import model


class TestUser(BaseTestCase):

    def test_hashPassword(self):
        result = model.User.hashPassword("test password" + UCHAR, "test salt" + UCHAR)
        assert result == "e6f8f799fe6c3081f5c5fc8880aba7e5e021d6cd8770cd94f24bf8ed5712c2695cb36abff90e8e1e3a18d2754aea520f0e3a675f3558bc018d3a3253a838049f"

    def test_getAuth(self):
        # the id and hashed_password are normally randomly generated
        # so we set them to fixed values here so we get consistent test results
        user = self.createUser(id="test key")
        user.hashed_password = "test hash"
        result = user.getAuth()
        assert result == "f8ddbf88b81c743c26fe0ff7aa40f70b7eb0a0f6fe577d71282c84c46aea5a204f9f82500cbb6bbfa4290bcde1ebbbe6717582b7d4af0787c75b7b1176242996"


class TestModelFunctions(BaseTestCase):

    def test_cache(self):
        self.executed = 0
        def testFunction():
            self.executed += 1
            return "test value"
        assert self.executed == 0

        result = model.cache("test key", testFunction)
        assert result == "test value"
        assert self.executed == 1

        # the value should now be cached, so the function should not be executed again
        result = model.cache("test key", testFunction)
        assert self.executed == 1
