# the base file and class for all controllers to inherit from

# python imports
import base64
import http.client
import json
import logging
import os

# library imports
from tornado import web

# local imports
import helpers
import model
from config.constants import AUTH_EXPIRES_DAYS, SUPPORT_EMAIL

# lib imports
from lib.gae_html import cacheAndRender # NOQA: F401

PROJECT = os.getenv('GOOGLE_CLOUD_PROJECT', 'test') # possibly 'APPLICATION_ID' ?


class BaseController(web.RequestHandler):

    def prepare(self):
        # get a session store for this request
        session = self.get_secure_cookie('session')
        if session:
            self.session = json.loads(session)
        else:
            self.session = {}

        if hasattr(self, "before"):
            # NOTE that self.path_args and self.path_kwargs are set as part of execute, so they aren't available here
            #      shouldn't be too much of a problem because any before method can inspect the entire request
            try:
                self.before()
            except Exception as e:
                raise

        # don't run the regular action if there's already an error or redirect
        status_int = self.get_status()
        if status_int < 200 or status_int > 299:
            raise web.Finish

    # override to do cleanup
    # def on_finish(self):
    # NOTE that cookies set here aren't returned in the response, so they won't be set
    # this should be used for server-side cleanup only - assume that the response cannot be modified at this point
    # sadly attempts to do so won't throw any errors, and the browser won't see the changes (silent failure)

    def saveSession(self):
        # this needs to be called anywhere we're finishing the response (rendering, redirecting, etc.)
        # FUTURE: optimize slightly by only doing this if the session has been modified
        #         tried something simply like `if self.session != self.orig_session:` and the cookie was never set
        self.set_secure_cookie('session', json.dumps(self.session), expires_days=AUTH_EXPIRES_DAYS,
            httponly=True, secure=not helpers.debug())

    @property
    def gcs_bucket(self):
        # this needs to change if not using the default bucket
        return PROJECT + '.appspot.com'

    @property
    def logger(self):
        return logging.getLogger('tornado.application')

    def flash(self, level, message):
        self.session["flash"] = {"level": level, "message": message}

    def compileTemplate(self, filename, **kwargs):

        # add some standard variables
        kwargs["is_admin"] = self.current_user and self.current_user.is_admin
        kwargs["is_dev"] = self.current_user and self.current_user.is_dev
        kwargs["form"] = self.session.pop("form_data", {})
        kwargs["errors"] = self.session.pop("errors", {})
        kwargs["h"] = helpers
        kwargs["page_title"] = kwargs.get("page_title", "")

        # flashes are a dict with two properties: {"level": "info|success|error", "message": "str"}
        kwargs["flash"] = self.session.pop("flash", {})

        return self.render_string(filename, **kwargs)

    def securityHeaders(self):
        # uncomment to enable HSTS - note that it can have permanent consequences for your domain
        # this header is removed from non appspot domains - a custom domain must be whitelisted first
        # see https://code.google.com/p/googleappengine/issues/detail?id=7427
        # self.set_header('Strict-Transport-Security', 'max-age=86400; includeSubDomains')

        # this is purposefully strict by default
        # you can change site-wide or add logic for different environments or actions as needed
        # see https://developers.google.com/web/fundamentals/security/csp/
        CSP = "default-src 'self'; form-action 'self'; "
        CSP += "base-uri 'none'; frame-ancestors 'none'; object-src 'none';"
        CSP += "report-uri " + self.request.host + "/policyviolation"
        self.set_header('Content-Security-Policy', CSP)

    def renderTemplate(self, filename, **kwargs):
        if self.request.method != 'HEAD':
            self.securityHeaders()
            # could have compile call `self.render` but it looks like a lot of extra processing we don't need
            self.write(self.compileTemplate(filename, **kwargs))
            self.saveSession()

    def renderError(self, status_int, stacktrace=None):
        self.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + http.client.responses[status_int]
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.set_header('Content-Type', 'application/json')
        if self.request.method != 'HEAD':
            self.write(data)
            self.saveSession()

    def head(self, *args):
        # support HEAD requests in a generic way
        if hasattr(self, 'get'):
            self.get(*args)
            # the output may be cached, but don't send it to save bandwidth
            self.clear()
        else:
            self.renderError(405)

    def redirect(self, *args, **kwargs):
        # saving the session needs to happen before the redirect for the cookies to be set
        self.saveSession()
        super(BaseController, self).redirect(*args, **kwargs)

    def redisplay(self, form_data=None, errors=None, url=None):
        """ redirects to the current page by default """
        if form_data is not None:
            self.session["form_data"] = form_data
        if errors is not None:
            self.session["errors"] = errors

        if url:
            self.redirect(url)
        else:
            self.redirect(self.request.path)

    # this overrides the base class for handling things like 500 errors
    def write_error(self, status_code, exc_info=None):
        # if this is development, then include a stack trace
        stacktrace = None
        message = None
        if exc_info and (helpers.debug() or (self.current_user and self.current_user.is_admin)):
            import traceback
            stacktrace = ''.join(traceback.format_exception(*exc_info))
            message = exc_info[0].__name__

        self.renderError(status_code, stacktrace=stacktrace)

        # send an email notifying about this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html", message=message,
            user=self.current_user, url=self.request.full_url(), method=self.request.method)

    # this is called automatically to set the current_user property
    def get_current_user(self):
        user = None
        slug = self.get_secure_cookie('auth_key')
        if slug:
            # secure cookies appear to always return bytes, and we need a string, so force it here
            slug = slug.decode()

            # uses a closure so we don't have to pass args
            def _get_user():
                user = None
                auth = model.Auth.getBySlug(slug, parent_class=model.User)
                if auth:
                    user = auth.user
                return user

            user = helpers.cache(slug, _get_user)
            if not user:
                self.clear_cookie('auth_key')
        return user

    def deferEmail(self, to, subject, filename, reply_to=None, attachments=None, **kwargs):
        params = {'to': to, 'subject': subject}

        if reply_to:
            params['reply_to'] = reply_to

        # this supports passing a template as well as a file
        if isinstance(filename, str):
            filename = "emails/" + filename

        # support passing in a custom host to prefix link
        if "host" not in kwargs:
            kwargs["host"] = self.request.host
        params['html'] = self.render_string(filename, **kwargs)

        if attachments:
            # attachments might contain binary data, which must be encoded to transport in the queue
            for attachment in attachments:
                attachment['content'] = base64.b64encode(attachment['content']).decode() # JSON needs strings
            params['attachments'] = json.dumps(attachments)

        # TODO: solution for this?
        # taskqueue.add(url='/job/email', params=params, queue_name='mail')


class FormController(BaseController):

    # a mapping of field names to their validator functions
    FIELDS = {}

    def validate(self):
        form_data = {} # all the original request data, for potentially re-displaying
        errors = {} # only fields with errors
        valid_data = {} # only valid fields

        for name, validator in self.FIELDS.items():
            # NOTE that checking for the unicode decode error happens inside get_argument

            form_data[name] = self.get_argument(name, default='', strip=False)

            valid, data = validator(form_data[name])
            if valid:
                valid_data[name] = data
            else:
                errors[name] = True

        return form_data, errors, valid_data


def withoutUser(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        if not controller.current_user:
            return action(*args, **kwargs)
        else:
            url = "/home"
            return controller.redirect(url)
    return decorate


def removeSlash(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        if controller.request.path.endswith("/"):
            return controller.redirect(controller.request.path[:-1], permanent=True)
        return action(*args, **kwargs)
    return decorate


def validateReferer(action):
    def decorate(*args, **kwargs):
        controller = args[0]
        referer = controller.request.headers.get("referer")
        if not referer or not referer.startswith("http://" + controller.request.headers.get("host")):
            return controller.renderError(400)
        return action(*args, **kwargs)
    return decorate
