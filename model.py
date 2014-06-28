from hashlib import sha512

from google.appengine.api import memcache
from google.appengine.ext import ndb

from config.constants import AUTH_SALT, PASSWORD_SALT


class User(ndb.Model):
    first_name = ndb.StringProperty(required=True)
    last_name = ndb.StringProperty(required=True)
    email = ndb.StringProperty(required=True)
    auth_pepper = ndb.StringProperty(required=True)
    password_pepper = ndb.StringProperty(required=True)
    hashed_password = ndb.StringProperty(required=True)
    is_admin = ndb.BooleanProperty(default=False)
    created_date = ndb.DateTimeProperty(auto_now_add=True)

    @classmethod
    def hashPassword(cls, password, pepper):
        return sha512(password.encode('utf8') + PASSWORD_SALT + pepper.encode('utf8')).hexdigest()

    def getAuth(self, ip_address):
        return sha512(self.key.urlsafe() + ip_address + AUTH_SALT + self.auth_pepper.encode('utf8')).hexdigest()


# model helper functions
def cache(key, function, expires=86400):
    value = memcache.get(key)
    if value is None:
        value = function()
        memcache.add(key, value, expires)
    return value

def toDict(model_object):
    """ convert a model object to a dictionary """
    d = {}
    for prop in model_object.properties():
        # we must avoid de-referencing the values for the reference properties
        if type(getattr(model_object.__class__, prop)) == db.ReferenceProperty:
            d[prop] = getattr(model_object.__class__, prop).get_value_for_datastore(model_object)
        else:
            d[prop] = getattr(model_object, prop)
    return d
