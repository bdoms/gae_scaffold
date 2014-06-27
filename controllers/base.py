# the base file and class for all controllers to inherit from

# python imports
import json
import logging
import sys

# app engine api imports
from google.appengine.api import memcache, users

# app engine included libraries imports
import jinja2
import webapp2
from webapp2_extras import sessions

# local imports
import helpers
from config.constants import TEMPLATES_PATH, LIB_PATH

# add lib to the path
sys.path.append(LIB_PATH)

# lib imports
from gae_html import cacheHTML, renderIfCached


class BaseController(webapp2.RequestHandler):

    jinja_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(TEMPLATES_PATH))

    def dispatch(self):
        # get a session store for this request
        self.session_store = sessions.get_store(request=self.request)

        if hasattr(self, "before"):
            try:
                self.before()
            except Exception as e:
                self.handle_exception(e, False)

        # only run the regular action if there isn't already an error or redirect
        if self.response.status_int == 200:
            webapp2.RequestHandler.dispatch(self)
        
        if hasattr(self, "after"):
            try:
                self.after()
            except Exception as e:
                self.handle_exception(e, False)

        # save all sessions
        self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # uses the default cookie key
        return self.session_store.get_session()

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
        template = self.jinja_env.get_template(filename)
        # add some standard variables
        kwargs["h"] = helpers
        kwargs["user"] = self.getUser()
        kwargs["is_admin"] = users.is_current_user_admin()
        if hasattr(self, "flash"):
            kwargs["flash"] = self.flash
        return template.render(kwargs)

    def render(self, html):
        self.response.out.write(html)

    def renderTemplate(self, filename, **kwargs):
        self.render(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int, stacktrace=None):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(data))

    # this overrides the base class for handling things like 500 errors
    def handle_exception(self, exception, debug):
        # log the error
        logging.exception(exception)

        # if this is development, then print out a stack trace
        stacktrace = None
        if helpers.debug():
            import traceback
            stacktrace = traceback.format_exc()

        # if the exception is a HTTPException, use its error code
        # otherwise use a generic 500 error code
        if isinstance(exception, webapp2.HTTPException):
            status_int = exception.code
        else:
            status_int = 500

        self.renderError(status_int, stacktrace=stacktrace)

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
