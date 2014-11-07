import os
from datetime import datetime
from hashlib import sha512

from google.appengine.api import memcache
from google.appengine.ext import ndb

from config.constants import PASSWORD_PEPPER, RESET_PEPPER


class User(ndb.Model):
    first_name = ndb.StringProperty(required=True)
    last_name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    password_salt = ndb.StringProperty(required=True)
    hashed_password = ndb.StringProperty(required=True)
    is_admin = ndb.BooleanProperty(default=False)
    created_date = ndb.DateTimeProperty(auto_now_add=True)

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

    def resetPasswordToken(self, timestamp=None):
        if not timestamp:
            timestamp = datetime.utcnow()
        now = timestamp.strftime('%Y%m%d%H') # hour resolution
        return sha512(now + self.hashed_password + RESET_PEPPER).hexdigest()


# model helper functions
def getByKey(str_key):
    entity = memcache.get(str_key)
    if not entity:
        try:
            key = ndb.Key(urlsafe=str_key)
        except:
            pass
        else:
            entity = key.get()
            memcache.add(str_key, entity)
    return entity

def cache(key, function, expires=86400):
    value = memcache.get(key)
    if value is None:
        value = function()
        memcache.add(key, value, expires)
    return value
