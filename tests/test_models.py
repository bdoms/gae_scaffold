from datetime import datetime

from base import BaseTestCase, UCHAR


class TestQuery(BaseTestCase):

    def test_fetch(self):
        self.createUser()
        q = self.model.Query(self.model.User)
        users = list(q.fetch())
        assert len(users) == 1
        assert isinstance(users[0], self.model.User)

        user_keys = list(q.fetch(keys_only=True))
        assert len(user_keys) == 1
        assert isinstance(user_keys[0], self.model.datastore.Key)

    def test_get(self):
        q = self.model.Query(self.model.User)
        user = q.get()
        assert not user

        self.createUser()
        user = q.get()
        assert user
        assert isinstance(user, self.model.User)


class TestBooleanProperty(BaseTestCase):

    def test_validate(self):
        prop = self.model.BooleanProperty()
        assert not prop.validate('1')
        assert not prop.validate(b'1')
        assert not prop.validate(1)
        assert not prop.validate(None)
        assert prop.validate(True)
        assert prop.validate(False)


class TestDatetimeProperty(BaseTestCase):

    def test_validate(self):
        prop = self.model.DateTimeProperty()
        assert not prop.validate('1')
        assert not prop.validate(b'1')
        assert not prop.validate(1)
        assert not prop.validate(True)
        assert prop.validate(datetime.utcnow())
        assert prop.validate(None)

        # if it's required then it can't be none
        prop = self.model.DateTimeProperty(required=True)
        assert not prop.validate(None)

    def test_default(self):
        prop = self.model.DateTimeProperty()
        assert prop.default is None

        prop = self.model.DateTimeProperty(auto_now_add=True)
        assert isinstance(prop.default, datetime)


class TestStringProperty(BaseTestCase):

    def test_validate(self):
        prop = self.model.StringProperty()
        assert not prop.validate(1)
        assert not prop.validate(True)
        assert not prop.validate(b'1')
        assert prop.validate('1')
        assert prop.validate(None)

        # required can't be none
        prop = self.model.StringProperty(required=True)
        assert not prop.validate(None)


class TestBytesProperty(BaseTestCase):

    def test_validate(self):
        prop = self.model.BytesProperty()
        assert not prop.validate(1)
        assert not prop.validate(None)
        assert not prop.validate(True)
        assert not prop.validate('1')
        assert prop.validate(b'1')

        # required can't be none
        prop = self.model.StringProperty(required=True)
        assert not prop.validate(None)


class TestBaseModel(BaseTestCase):

    def test_put(self):
        self.createUser()
        self.user.put()
        assert self.user.key == self.user.entity.key

    def test_update(self):
        self.createUser()
        first_name = 'new test value'
        self.user.update(unknown_prop='value', first_name=first_name)
        assert not self.user.entity.get('unknown_prop')
        assert not getattr(self.user, 'unknown_prop', None)
        assert self.user.entity['first_name'] == first_name
        assert self.user.first_name == first_name

    def test_create(self):
        # only the required data
        data = {
            'first_name': 'test_first',
            'last_name': 'test_last',
            'email': 'test_email',
            'password_salt': b'test_salt',
            'hashed_password': 'test_hashed'
        }
        user = self.model.User.create(**data)
        assert user
        assert isinstance(user, self.model.User)
        for key, value in data.items():
            assert user.entity[key] == value
            assert getattr(user, key, None) == value

        # now with a parent
        user.put() # so we can use it as a parent
        data = {'user_agent': 'test_ua', 'ip': 'test_ip'}
        auth = self.model.Auth.create(parent_key=user.key, **data)
        assert auth
        assert auth.key.parent == user.key

    def test_slugToKey(self):
        key = self.model.BaseModel.slugToKey('123')
        assert isinstance(key, self.model.datastore.Key)

        key = self.model.BaseModel.slugToKey('123.456', parent_class=self.model.BaseModel)
        assert isinstance(key, self.model.datastore.Key)

    def test_getBySlug(self):
        created_user = self.createUser()
        gotten_user = self.model.User.getBySlug(created_user.slug)
        assert gotten_user
        assert created_user.key == gotten_user.key

    def test_properties(self):
        props = self.model.BaseModel.properties()
        assert len(props) == 2
        assert 'created_dt' in props
        assert 'modified_dt' in props

    def test_query(self):
        q = self.model.BaseModel.query()
        assert q
        assert isinstance(q, self.model.datastore.query.Query)


class TestUser(BaseTestCase):

    def stubUrandom(self, n):
        return b"constant"

    def test_slug(self):
        self.createUser()
        assert self.user.slug
        assert isinstance(self.user.slug, str)

    def test_auths(self):
        self.createAuth()
        auths = list(self.user.auths)
        assert len(auths) == 1
        assert isinstance(auths[0], self.model.Auth)

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
        self.createAuth()
        auth = self.user.getAuth(self.auth.user_agent)
        assert auth
        assert auth.key == self.auth.key

    def test_resetPassword(self):
        user = self.createUser()

        # stub the os urandom method so that we get constant results
        orig = self.model.os.urandom
        self.model.os.urandom = self.stubUrandom

        user = user.resetPassword()

        # revert the stub to the original now that the method has been called
        self.model.os.urandom = orig

        assert user.token == "Y29uc3RhbnQ" # "constant" base64 encoded for URLs
        assert (datetime.utcnow() - user.token_dt).total_seconds() < 1 # should be very fresh


class TestAuth(BaseTestCase):

    def test_user(self):
        self.createAuth()
        assert isinstance(self.auth.user, self.model.User)

    def test_slug(self):
        self.createAuth()
        assert self.auth.slug
        assert isinstance(self.auth.slug, str)
        assert '.' in self.auth.slug # denotes a parent
