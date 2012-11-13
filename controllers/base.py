# the base file and class for all controllers to inherit from

# python imports
import sys

# app engine imports
from google.appengine.api import memcache, users
from django.utils import simplejson
import webapp2

# local imports
import helpers
from config import TEMPLATES_PATH, LIB_PATH

# must use same import for sessions as the middleware
from lib.gaesessions import get_current_session

# add lib to the path
sys.path.append(LIB_PATH)

# lib imports
from mako.lookup import TemplateLookup
from gae_html import cacheHTML, renderIfCached


class BaseController(webapp2.RequestHandler):

    template_lookup = TemplateLookup(directories=[TEMPLATES_PATH], input_encoding='utf-8')

    # add support for before and after methods on get and post requests
    def __getattribute__(self, name):
        if name in ["get", "post"]:
            if hasattr(self, "before"):
                self.before()
            # don't run the regular action if there's already an error
            if self.response.status_int == 200:
                value = webapp2.RequestHandler.__getattribute__(self, name)
            else:
                def value(*args, **kwargs): pass
            if hasattr(self, "after"):
                self.after()
        else:
            value = webapp2.RequestHandler.__getattribute__(self, name)
        return value

    def cacheAndRenderTemplate(self, filename, **kwargs):
        def renderHTML():
            return self.compileTemplate(filename, **kwargs)
        # don't cache when there's a flash message
        if hasattr(self, "flash"):
            html = renderHTML()
        else:
            html = cacheHTML(self, renderHTML, **kwargs)
        return self.render(html)

    def compileTemplate(self, filename, **kwargs):
        template = self.template_lookup.get_template(filename)
        # add some standard variables
        kwargs["h"] = helpers
        kwargs["user"] = self.getUser()
        kwargs["is_admin"] = users.is_current_user_admin()
        if hasattr(self, "flash"):
            kwargs["flash"] = self.flash
        return template.render_unicode(**kwargs)

    def render(self, html):
        self.response.out.write(html)

    def renderTemplate(self, filename, **kwargs):
        self.render(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", page_title=page_title)

    def renderJSON(self, data):
        self.response.out.write(simplejson.dumps(data))

    def cache(self, key, function, expires=86400):
        value = memcache.get(key)
        if value is None or helpers.debug():
            value = function()
            if not users.is_current_user_admin():
                memcache.add(key, value, expires)
        return value

    def getUser(self):
        user = None
        if hasattr(self, "user"):
            user = self.user
        else:
            user = users.get_current_user()
            self.user = user
        return user


def withSession(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        session = get_current_session()
        if session:
            if not session.is_active() or not session.sid:
                session.regenerate_id()
        else:
            # this can happen during tests
            session = {}
        controller.session = session
        return action(*args, **kwargs)
    return decorate


def removeSlash(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        if controller.request.path.endswith("/"):
            return controller.redirect(controller.request.path[:-1], permanent=True)
        return action(*args, **kwargs)
    return decorate


def validateReferer(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        referer = controller.request.headers.get("referer")
        if not helpers.debug() and not referer.startswith("http://" + controller.request.headers.get("host")):
            return controller.renderError(400)
        return action(*args, **kwargs)
    return decorate
