import os
import re
from urllib import quote_plus

from google.appengine.api import memcache, users

from lib.gae_deploy import static, DEBUG

TESTING = os.environ.get('SERVER_SOFTWARE', '') == ('DevelopmentTesting')


def debug():
    # determine whether we're serving on development or production
    return DEBUG

def testing():
    return TESTING

def natural_list(string_list):
    # takes a list of strings and renders them like a natural language list
    list_len = len(string_list)
    if list_len == 0:
        return ""
    elif list_len == 1:
        return string_list[0]
    else:
        last_index = len(string_list) - 1
        last_item = string_list[last_index]
        first_items = ', '.join(string_list[:last_index])
        return first_items + " and " + last_item

def url_quote(s):
    return quote_plus(s.encode("utf-8"))

def attr_escape(s):
    return s.replace('"', '&quot;')

def strip_html(string):
    return re.sub(r'<[^<]*?/?>', '', string)

def limit(string, max_len):
    if len(string) > max_len:
        string = string[0:max_len - 3] + "..."
    return string

def int_comma(i):
    # takes an int and returns it with commas every three digits
    s = str(i)
    groups = []
    while s and s[-1].isdigit():
        groups.append(s[-3:])
        s = s[:-3]
    return s + ','.join(reversed(groups))

def get_cache(key):
    value = memcache.get(key)
    # don't use cached versions in development or for admins
    if value and not debug() and not users.is_current_user_admin():
        return value
    return None

def store_cache(key, value, expires=86400): # cache for 1 day by default
    if not users.is_current_user_admin(): # don't cache the admin version of a page
        memcache.add(key, value, expires)

