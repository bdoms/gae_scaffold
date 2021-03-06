import base64
import os
from datetime import datetime
from hashlib import sha512

from google.appengine.api import memcache
from google.appengine.ext import ndb

from config.constants import PASSWORD_PEPPER


class User(ndb.Model):
    first_name = ndb.StringProperty(required=True)
    last_name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    password_salt = ndb.StringProperty(required=True)
    hashed_password = ndb.StringProperty(required=True)
    token = ndb.StringProperty()
    token_date = ndb.DateTimeProperty()
    pic_gcs = ndb.StringProperty()
    pic_blob = ndb.BlobKeyProperty()
    pic_url = ndb.StringProperty()
    is_admin = ndb.BooleanProperty(default=False)
    created_date = ndb.DateTimeProperty(auto_now_add=True)

    @property
    def slug(self):
        return self.key.urlsafe()

    @property
    def auths(self):
        return Auth.query(ancestor=self.key).order(-Auth.last_login)

    @classmethod
    def getByEmail(cls, email):
        return cls.query(cls.email == email).get()

    @classmethod
    def hashPassword(cls, password, salt):
        return sha512(password.encode('utf8') + salt.encode('utf8') + PASSWORD_PEPPER).hexdigest()

    @classmethod
    def changePassword(cls, password):
        salt = os.urandom(64).encode("base64")
        hashed_password = cls.hashPassword(password, salt)
        return salt, hashed_password

    def getAuth(self, user_agent):
        return Auth.query(Auth.user_agent == user_agent, ancestor=self.key).get()

    def resetPassword(self):
        # python b64 always ends in '==' so we remove them because this is for use in a URL
        self.token = base64.urlsafe_b64encode(os.urandom(16)).replace('=', '')
        self.token_date = datetime.utcnow()
        self.put()
        uncache(self.slug)
        return self


class Auth(ndb.Model):
    user_agent = ndb.StringProperty(required=True)
    os = ndb.StringProperty(required=True)
    browser = ndb.StringProperty(required=True)
    device = ndb.StringProperty(required=True)
    ip = ndb.StringProperty(required=True)
    first_login = ndb.DateTimeProperty(auto_now_add=True)
    last_login = ndb.DateTimeProperty(auto_now=True)

    @property
    def user(self):
        return self.key.parent().get()


# model helper functions
def getByKey(str_key):
    entity = None
    if str_key:
        entity = memcache.get(str_key)
        if not entity:
            try:
                key = ndb.Key(urlsafe=str_key)
            except Exception:
                pass
            else:
                entity = key.get()
                if entity:
                    memcache.add(str_key, entity)
    return entity


def cache(key, function, expires=86400):
    value = memcache.get(key)
    if value is None:
        value = function()
        memcache.add(key, value, expires)
    return value


def uncache(key, seconds=10):
    memcache.delete(key, seconds=seconds)
