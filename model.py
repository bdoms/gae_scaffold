import base64
import inspect
import os
from datetime import datetime
from hashlib import sha512

from google.cloud import datastore

from config.constants import PASSWORD_PEPPER, DATASTORE_EMULATOR_HOST
import helpers

if helpers.debug():
    # TODO: this should be within a check for the dev env
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


class BaseModel(object):

    def __init__(self, entity):
        self.entity = entity
        self._updateProps()
        self.key = entity.key

    def _updateProps(self):
        for prop in self.__class__.properties():
            setattr(self, prop, self.entity.get(prop, None))

    def put(self):
        db.put(self.entity)

    def update(self, **kwargs):
        data = {}
        for prop in self.__class__.properties():
            prop_object = getattr(self.__class__, prop)
            if prop in kwargs:
                value = kwargs[prop]
                if prop_object.validate(value):
                    data[prop] = value
                else:
                    raise ValueError('"{}" is not a valid "{}"'.format(prop, prop_object.__class__.__name__))
            elif hasattr(prop_object, 'auto_now'):
                data[prop] = datetime.utcnow()

        self.entity.update(data)
        self._updateProps()

    @classmethod
    def create(cls, parent=None, **kwargs):
        entity = datastore.Entity(db.key(cls.__name__, parent=parent))
        # TODO
        # entity.update({
        #     'category': 'Personal',
        #     'done': False,
        #     'priority': 4,
        #     'description': 'Learn Cloud Datastore'
        # })
        for prop in cls.properties():
            value = None
            prop_object = getattr(cls, prop)
            if prop in kwargs:
                value = kwargs[prop]
                if not prop_object.validate(value):
                    raise ValueError('"{}" is not a valid "{}"'.format(prop, prop_object.__class__.__name__))

            if value is None and hasattr(prop_object, 'default'):
                # TODO: for an update routine, make sure that the default isn't already set on this entity
                #       also need to support auto_now in an update
                value = prop_object.default

            kwargs[prop] = value

        entity.update(kwargs)
        return cls(entity)

    @classmethod
    def properties(cls):
        # inspect.getmembers returns a tuple of (name, type) but we only want the name
        return [prop[0] for prop in inspect.getmembers(cls, lambda prop: isinstance(prop, BaseProperty))]

    @classmethod
    def query(cls, *args, **kwargs):
        return db.query(kind=cls.__name__, *args, **kwargs)

    @classmethod
    def get(cls, query):
        # acts like the old .get where it returns the first entity or None
        results = list(query.fetch(limit=1))
        return results and cls(results[0]) or None

    @classmethod
    def getBySlug(cls, slug, parent_class=None):
        # assumes max 2 levels deep for now
        if parent_class:
            ids = slug.split('.')
            path = [parent_class.__name__, int(ids[0]), cls.__name__, int(ids[1])]
        else:
            path = [cls.__name__, int(slug)]
        key = db.key(*path)
        entity = db.get(key)
        return entity and cls(entity) or None


class BaseProperty(object):

    def validate(self, value):
        raise NotImplemented


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
    created_date = DateTimeProperty(auto_now_add=True)

    @property
    def slug(self):
        return str(self.key.id)

    @property
    def auths(self):
        return Auth.query(ancestor=self.key, order=['-last_login']).fetch()

    @classmethod
    def getByEmail(cls, email):
        q = cls.query()
        q.add_filter('email', '=', email)
        return cls.get(q)

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
        return Auth.get(q)

    def resetPassword(self):
        # python b64 always ends in '==' so we remove them because this is for use in a URL
        self.token = base64.urlsafe_b64encode(os.urandom(16)).replace('=', '')
        self.token_date = datetime.utcnow()
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
