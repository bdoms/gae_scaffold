# the base file and class for all controllers to inherit from

# python imports
import json
import logging
import os

# app engine api imports
from google.appengine.api import memcache, users
from google.appengine.ext import ndb

# app engine included libraries imports
import jinja2
import webapp2
from webapp2_extras import sessions

# local imports
import helpers
import model
from config.constants import TEMPLATES_PATH

# lib imports
from lib.gae_html import cacheHTML, renderIfCached


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

    def flash(self, level, message):
        self.session["flash"] = {"level": level, "message": message}

    def cacheAndRenderTemplate(self, filename, **kwargs):
        def renderHTML():
            return self.compileTemplate(filename, **kwargs)
        # don't cache when there's a flash message
        if "flash" in self.session:
            html = renderHTML()
        else:
            html = cacheHTML(self, renderHTML, **kwargs)
        return self.response.out.write(html)

    def compileTemplate(self, filename, **kwargs):
        template = self.jinja_env.get_template(filename)
        # add some standard variables
        kwargs["h"] = helpers
        kwargs["user"] = user = self.user
        kwargs["is_admin"] = user and user.is_admin
        kwargs["is_dev"] = users.is_current_user_admin()
        kwargs["form"] = self.session.pop("form_data", {})
        kwargs["errors"] = self.session.pop("errors", {})
        # flashes are a dict with two properties: {"level": "info|success|error", "message": "str"}
        kwargs["flash"] = self.session.pop("flash", {})
        return template.render(kwargs)

    def renderTemplate(self, filename, **kwargs):
        self.response.out.write(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int, stacktrace=None):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        self.response.out.write(json.dumps(data, ensure_ascii=False, encoding='utf-8'))

    # this overrides the base class for handling things like 500 errors
    def handle_exception(self, exception, debug):
        # log the error
        logging.exception(exception)

        # if this is development, then print out a stack trace
        stacktrace = None
        if helpers.debug() or (self.user and self.user.is_admin):
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
        if value is None:
            value = function()
            memcache.add(key, value, expires)
        return value

    def uncache(self, key, seconds=0):
        memcache.delete(key, seconds=seconds)

    @webapp2.cached_property
    def user(self):
        user = None
        if 'user_key' in self.session:
            str_key = self.session['user_key']
            user = memcache.get(str_key)
            if not user:
                try:
                    user_key = ndb.Key(urlsafe=str_key)
                except:
                    pass
                else:
                    user = user_key.get()
                    memcache.add(str_key, user)

            user_auth = self.session.get("user_auth")
            if not user or not user_auth or user_auth != user.getAuth():
                user = None
                del self.session['user_key']
        return user


class FormController(BaseController):

    # a mapping of field names to their validator functions
    FIELDS = {}

    def validate(self):
        form_data = {} # all the original request data, for potentially re-displaying
        errors = {} # only fields with errors
        valid_data = {} # only valid fields

        for name, validator in self.FIELDS.items():
            form_data[name] = self.request.get(name)
            valid, data = validator(form_data[name])
            if valid:
                valid_data[name] = data
            else:
                errors[name] = True

        return form_data, errors, valid_data

    def redisplay(self, form_data, errors, url):
        self.session["form_data"] = form_data
        self.session["errors"] = errors
        self.redirect(url)


def withUser(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        if controller.user:
            return action(*args, **kwargs)
        else:
            url = "/login"
            return controller.redirect(url)
    return decorate


def withoutUser(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        if not controller.user:
            return action(*args, **kwargs)
        else:
            url = "/home"
            return controller.redirect(url)
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
        if not referer.startswith("http://" + controller.request.headers.get("host")):
            return controller.renderError(400)
        return action(*args, **kwargs)
    return decorate
