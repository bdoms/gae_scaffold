import base64
import inspect
import os
from datetime import datetime
from hashlib import sha512

from google.cloud import datastore

from config.constants import PASSWORD_PEPPER, DATASTORE_EMULATOR_HOST
import helpers

if helpers.debug():
    # have to mock the call because dev_appserver doesn't properly set up the app engine environment (yet)
    # note that using mock.patch doesn't seem to work here (don't know why)
    import mock
    import google.auth
    from google.auth import credentials
    creds = mock.Mock(spec=credentials.Credentials)
    google.auth.default = lambda: (creds, os.getenv('GOOGLE_CLOUD_PROJECT', 'test'))

    os.environ['DATASTORE_EMULATOR_HOST'] = DATASTORE_EMULATOR_HOST

# NOTE if you want to do different namespaces you can pass one to the client here and it'll use it by default

# https://googleapis.github.io/google-cloud-python/latest/datastore/client.html
db = datastore.Client() # credentials=creds, #project='test')

# TODO: production should either look like this:
#db = datastore.Client() # auto from app engine env
# or maybe this:
# db = datastore.Client(os.getenv('GOOGLE_CLOUD_PROJECT', ''))


class Query(datastore.query.Query):

    def __init__(self, model_class, *args, **kwargs):
        super().__init__(db, kind=model_class.__name__, *args, **kwargs)
        self.model_class = model_class

    def __iter__(self):
        return (self.model_class(result) for result in super().fetch())

    def fetch(self, keys_only=False, *args, **kwargs):
        if keys_only:
            super().keys_only()

        for result in super().fetch(*args, **kwargs):
            yield self.model_class(result)

    def get(self):
        # acts like the old .get where it returns the first entity or None
        results = list(super().fetch(limit=1))
        return results and self.model_class(results[0]) or None


class BaseModel(object):

    def __init__(self, entity, create=False, **kwargs):
        self.entity = entity
        self.key = entity.key

        if create:
            self._updateEntity(create=create, **kwargs)

        self._updateProps()

    def _updateEntity(self, create=False, **kwargs):
        data = {}
        for prop in self.__class__.properties():
            value = None
            prop_object = getattr(self.__class__, prop)
            if prop in kwargs:
                value = kwargs[prop]
                if not prop_object.validate(value):
                    raise ValueError('"{}" is not a valid "{}"'.format(prop, prop_object.__class__.__name__))
            elif hasattr(prop_object, 'auto_now') and prop_object.auto_now:
                # this is above create because it applies to both create and update
                value = datetime.utcnow()
            elif create:
                if hasattr(prop_object, 'default'):
                    value = prop_object.default
            else:
                # default to any pre-existing value
                value = self.entity.get(prop, None)

            data[prop] = value

        self.entity.update(data)

    def _updateProps(self):
        for prop in self.__class__.properties():
            setattr(self, prop, self.entity.get(prop, None))

    def put(self):
        db.put(self.entity)
        self.key = self.entity.key

    def update(self, **kwargs):
        self._updateEntity(**kwargs)
        self._updateProps()

    @classmethod
    def create(cls, parent=None, **kwargs):
        entity = datastore.Entity(db.key(cls.__name__, parent=parent))
        return cls(entity, create=True, **kwargs)

    @classmethod
    def slugToKey(cls, slug, parent_class=None):
        # assumes max 2 levels deep for now
        if parent_class:
            ids = slug.split('.')
            path = [parent_class.__name__, int(ids[0]), cls.__name__, int(ids[1])]
        else:
            path = [cls.__name__, int(slug)]
        return db.key(*path)

    @classmethod
    def getBySlug(cls, slug, parent_class=None):
        key = cls.slugToKey(slug, parent_class=parent_class)
        entity = db.get(key)
        return entity and cls(entity) or None

    @classmethod
    def properties(cls):
        # inspect.getmembers returns a tuple of (name, type) but we only want the name
        return [prop[0] for prop in inspect.getmembers(cls, lambda prop: isinstance(prop, BaseProperty))]

    @classmethod
    def query(cls, *args, **kwargs):
        return Query(cls, *args, **kwargs)


class BaseProperty(object):

    def validate(self, value):
        raise NotImplementedError


class BooleanProperty(BaseProperty):

    def __init__(self, default=False):
        self.default = default

    def validate(self, value):
        return isinstance(value, bool)


class DateTimeProperty(BaseProperty):

    def __init__(self, auto_now_add=False, auto_now=False):
        self.auto_now_add = auto_now_add
        self.auto_now = auto_now

    def validate(self, value):
        return isinstance(value, datetime)

    @property
    def default(self):
        if self.auto_now_add:
            return datetime.utcnow()
        return None


class StringProperty(BaseProperty):

    def __init__(self, required=False):
        self.required = required

    def validate(self, value):
        if not isinstance(value, str):
            return False
        if self.required and not value:
            return False
        return True


class BytesProperty(BaseProperty):

    def __init__(self, required=False):
        self.required = required

    def validate(self, value):
        if not isinstance(value, bytes):
            return False
        if self.required and not value:
            return False
        return True


class User(BaseModel):
    first_name = StringProperty(required=True)
    last_name = StringProperty(required=True)
    email = StringProperty(required=True)
    password_salt = BytesProperty(required=True)
    hashed_password = StringProperty(required=True)
    token = StringProperty()
    token_date = DateTimeProperty()
    pic_gcs = StringProperty()
    #pic_blob = BlobKeyProperty()
    pic_url = StringProperty()
    is_admin = BooleanProperty(default=False)
    is_dev = BooleanProperty(default=False) # set this directly via the datastore console
    created_date = DateTimeProperty(auto_now_add=True)

    @property
    def slug(self):
        return str(self.key.id)

    @property
    def auths(self):
        return Auth.query(ancestor=self.key, order=['-last_login'])

    @classmethod
    def getByEmail(cls, email):
        q = cls.query()
        q.add_filter('email', '=', email)
        return q.get()

    @classmethod
    def hashPassword(cls, password, salt):
        return sha512(password.encode('utf8') + salt + PASSWORD_PEPPER).hexdigest()

    @classmethod
    def changePassword(cls, password):
        salt = base64.b64encode(os.urandom(64))
        hashed_password = cls.hashPassword(password, salt)
        return salt, hashed_password

    def getAuth(self, user_agent):
        q = Auth.query(ancestor=self.key)
        q.add_filter('user_agent', '=', user_agent)
        return q.get()

    def resetPassword(self):
        # python b64 always ends in '==' so we remove them because this is for use in a URL
        self.update(token=base64.urlsafe_b64encode(os.urandom(16)).decode().replace('=', ''),
            token_date=datetime.utcnow())
        self.put()
        return self


class Auth(BaseModel):
    user_agent = StringProperty(required=True)
    os = StringProperty()
    browser = StringProperty()
    device = StringProperty()
    ip = StringProperty(required=True)
    first_login = DateTimeProperty(auto_now_add=True)
    last_login = DateTimeProperty(auto_now=True)

    @property
    def user(self):
        entity = db.get(self.key.parent)
        return entity and User(entity)

    @property
    def slug(self):
        path = self.key.flat_path
        return str(path[1]) + '.' + str(path[3])
