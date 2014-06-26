from google.appengine.api import memcache
from google.appengine.ext import ndb


class User(ndb.Model):
  first_name = ndb.StringProperty(required=True)
  last_name = ndb.StringProperty(required=True)
  is_admin = ndb.BooleanProperty(default=False)
  created_date = ndb.DateTimeProperty(auto_now_add=True)


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
