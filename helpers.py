import os
import re
from urllib.parse import quote_plus

from lib.gae_deploy import static, script, style # NOQA: F401

DEBUG = os.getenv('GAE_ENV', 'localdev').startswith('localdev') # "standard" on production (maybe "flexible" too?)
TESTING = '(testbed)' in os.environ.get('SERVER_SOFTWARE', '')

CACHE = {}
CACHE_KEYS = []
CACHE_MAX_SIZE = 128 # number of unique entries


def debug():
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
    return re.sub(r'<[^<]*?/?>', '', string).strip()


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


def cache(key, function):
    # simple in memory LRU cache, most recently used key is moved to the end, least is at front
    if key in CACHE:
        # move the key to the end since it was just used
        # (this method avoids a temporary state with the key not existing that might not be threadsafe)
        CACHE_KEYS.sort(key=key.__eq__)
        return CACHE[key]

    while len(CACHE_KEYS) >= CACHE_MAX_SIZE:
        remove_key = CACHE_KEYS.pop(0)
        del CACHE[remove_key]

    value = function()
    CACHE_KEYS.append(key)
    CACHE[key] = value
    return value


def uncache(key):
    if key in CACHE:
        del CACHE[key]
        CACHE_KEYS.remove(key)


def clear_cache():
    global CACHE, CACHE_KEYS
    CACHE = {}
    CACHE_KEYS = []
