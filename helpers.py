import os
import re
from urllib import quote_plus

from google.appengine.api import memcache, users

from lib.gae_deploy import static, script, style, DEBUG

TESTING = '(testbed)' in os.environ.get('SERVER_SOFTWARE', '')


def debug():
    # determine whether we're serving on development or production
    return DEBUG

def testing():
    return TESTING

def host():
    host = os.environ.get('HTTP_ORIGIN')
    if not host:
        protocol = os.environ.get('HTTPS') == 'off' and 'http://' or 'https://'
        host = protocol + os.environ['HTTP_HOST']
    return host

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

def plural(string):
    last = string[-1]
    if last == "y":
        string = string[:-1] + "ies"
    elif last != "s":
        string += "s"
    return string

def nl2br(string):
    return string.replace("\n", "<br/>")

ORDINALS = ["First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth", "Ninth", "Tenth"]
def ordinal(i):
    if i <= len(ORDINALS):
        return ORDINALS[i - 1]
    else:
        s = str(i)
        last_two = s[-2:]
        if last_two in ["11", "12", "13"]:
            return s + "th"
        else:
            last = s[-1]
            if last == "1":
                return s + "st"
            elif last == "2":
                return s + "nd"
            elif last == "3":
                return s + "rd"
            else:
                return s + "th"

def money(i):
    # display an int in cents properly formatted as dollars
    s = str(i)
    while len(s) < 3:
        s = "0" + s
    return "$" + int_comma(s[:-2]) + "." + s[-2:]   

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

