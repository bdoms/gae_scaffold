# the base file and class for all controllers to inherit from

# python imports
import json
import logging
import urllib2

# app engine api imports
from google.appengine.api import app_identity, mail, memcache, users
from google.appengine.ext import deferred

# app engine included libraries imports
import jinja2
import webapp2
from webapp2_extras import sessions

# local imports
import helpers
import model
from config.constants import VIEW_PATH, SENDGRID_API_KEY, SENDER_EMAIL, SUPPORT_EMAIL

# lib imports
from gae_html import cacheAndRender
import sendgrid
from sendgrid.helpers import mail as sgmail


class BaseController(webapp2.RequestHandler):

    jinja_env = jinja2.Environment(loader=jinja2.FileSystemLoader(VIEW_PATH))

    def dispatch(self):
        # get a session store for this request
        self.session_store = sessions.get_store(request=self.request)

        if hasattr(self, "before"):
            try:
                self.before(*self.request.route_args, **self.request.route_kwargs)
            except Exception as e:
                self.handle_exception(e, False)

        # only run the regular action if there isn't already an error or redirect
        if self.response.status_int == 200:
            webapp2.RequestHandler.dispatch(self)
        
            if hasattr(self, "after"):
                try:
                    self.after(*self.request.route_args, **self.request.route_kwargs)
                except Exception as e:
                    self.handle_exception(e, False)

        # save all sessions
        self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # uses the default cookie key
        return self.session_store.get_session()

    @webapp2.cached_property
    def gcs_bucket(self):
        # this needs to change if not using the default bucket
        return app_identity.get_default_gcs_bucket_name()

    def flash(self, level, message):
        self.session["flash"] = {"level": level, "message": message}

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

    def render(self, content):
        # uncomment to enable HSTS - note that it can have permanent consequences for your domain
        # this header is removed from non appspot domains - a custom domain must be whitelisted first
        # see https://code.google.com/p/googleappengine/issues/detail?id=7427
        # self.response.headers['Strict-Transport-Security'] = 'max-age=86400; includeSubDomains'

        # this is purposefully strict by default
        # you can change site-wide or add logic for different environments or actions as needed
        # see https://developers.google.com/web/fundamentals/security/csp/
        CSP = "default-src 'self'; form-action 'self'; "
        CSP += "base-uri 'none'; frame-ancestors 'none'; object-src 'none';"
        CSP += "report-uri " + self.request.host_url + "/policyviolation"
        self.response.headers['Content-Security-Policy'] = CSP

        self.response.out.write(content)

    def renderTemplate(self, filename, **kwargs):
        if self.request.method != 'HEAD':
            self.render(self.compileTemplate(filename, **kwargs))

    def renderError(self, status_int, stacktrace=None):
        self.response.set_status(status_int)
        page_title = "Error " + str(status_int) + ": " + self.response.http_status_message(status_int)
        self.renderTemplate("error.html", stacktrace=stacktrace, page_title=page_title)

    def renderJSON(self, data):
        self.response.headers['Content-Type'] = "application/json"
        if self.request.method != 'HEAD':
            self.render(json.dumps(data, ensure_ascii=False, encoding='utf-8'))

    def head(self, *args):
        # support HEAD requests in a generic way
        if hasattr(self, 'get'):
            self.get(*args)
            # the output may be cached, but don't send it to save bandwidth
            self.response.clear()
        else:
            self.renderError(405)

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

        # send an email notifying about this error
        self.deferEmail([SUPPORT_EMAIL], "Error Alert", "error_alert.html", exception=exception,
            user=self.user, url=self.request.url, method=self.request.method)

    def cache(self, key, function, expires=86400):
        value = memcache.get(key)
        if value is None:
            value = function()
            memcache.add(key, value, expires)
        return value

    def uncache(self, key, seconds=10):
        memcache.delete(key, seconds=seconds)

    @webapp2.cached_property
    def user(self):
        user = None
        if 'auth_key' in self.session:
            str_key = self.session['auth_key']
            auth = model.getByKey(str_key)
            if auth:
                user = auth.user
            else:
                del self.session['auth_key']
        return user

    @classmethod
    def sendEmail(cls, to, subject, html, reply_to=None):
        body = helpers.strip_html(html)

        if SENDGRID_API_KEY:
            message = sgmail.Mail()
            message.set_from(sgmail.Email(SENDER_EMAIL))
            message.set_subject(subject)
            # NOTE that plain must come first
            message.add_content(sgmail.Content('text/plain', body))
            message.add_content(sgmail.Content('text/html', html))

            personalization = sgmail.Personalization()
            for to_email in to:
                personalization.add_to(sgmail.Email(to_email))
            message.add_personalization(personalization)

            if reply_to:
                message.set_reply_to(sgmail.Email(reply_to))

            if helpers.debug():
                mail_settings = sgmail.MailSettings()
                mail_settings.set_sandbox_mode(sgmail.SandBoxMode(True))
                message.set_mail_settings(mail_settings)

            api = sendgrid.SendGridAPIClient(apikey=SENDGRID_API_KEY)
            
            # an error here logs the status code but not the message
            # which is way more helpful, so we get it manually
            try:
                response = api.client.mail.send.post(request_body=message.get())
            except urllib2.HTTPError, e:
                logging.error(e.read())
        else:
            for to_email in to:
                if reply_to:
                    mail.send_mail(sender=SENDER_EMAIL, to=to_email, subject=subject, body=body, html=html,
                        reply_to=reply_to)
                else:
                    mail.send_mail(sender=SENDER_EMAIL, to=to_email, subject=subject, body=body, html=html)

    @classmethod
    def fanoutEmail(cls, to, subject, body, reply_to=None):
        # do it in batches and continue to fan out to minimize chance that it gets stuck
        batch_size = 5
        deferred.defer(cls.sendEmail, to[:batch_size], subject, body, reply_to=reply_to, _queue="mail")

        leftovers = to[batch_size:]
        if leftovers:
            deferred.defer(cls.fanoutEmail, leftovers, subject, body, reply_to=reply_to, _queue="mail")

    def deferEmail(self, to, subject, filename, reply_to=None, **kwargs):
        # this supports passing a template as well as a file
        if type(filename) == type(""):
            filename = "emails/" + filename
        template = self.jinja_env.get_template(filename)

        # support passing in a custom host to prefix link
        if "host" not in kwargs:
            kwargs["host"] = self.request.host_url
        html = template.render(kwargs)

        self.fanoutEmail(to, subject, html, reply_to=reply_to)


class FormController(BaseController):

    # a mapping of field names to their validator functions
    FIELDS = {}

    def validate(self):
        form_data = {} # all the original request data, for potentially re-displaying
        errors = {} # only fields with errors
        valid_data = {} # only valid fields

        for name, validator in self.FIELDS.items():
            try:
                form_data[name] = self.request.get(name)
            except UnicodeDecodeError:
                return self.renderError(400)
            
            valid, data = validator(form_data[name])
            if valid:
                valid_data[name] = data
            else:
                errors[name] = True

        return form_data, errors, valid_data


def withUser(action):
    def decorate(*args,  **kwargs):
        controller = args[0]
        if controller.user:
            return action(*args, **kwargs)
        else:
            url = "/user/login"
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


# NOTE: because of how chaining of __init__ and private (double underscore) variables work with multiple inheritance
#       (see http://stackoverflow.com/questions/8688114/python-multi-inheritance-init)
#       the blobstore UploadHandler must come first. On the server (both dev and prod) everything works as expected,
#       but webtest uses the first webapp platform it encounters, which is webapp 1 for the UploadHandler,
#       (whereas the BaseController uses webapp2) and webapp 1 doesn't use the dispatch method
#       which is why we have this custom second-level decorator defined to call it manually.
def testDispatch(action):
    class MockApp(object):
        debug = True
    def decorate(*args,  **kwargs):
        if helpers.testing():
            controller = args[0]
            # this will go into an infinite loop of dispatching itself if we don't stop it
            if hasattr(controller, 'dispatch_called'):
                return action(*args, **kwargs)
            else:
                controller.app = MockApp()
                controller.dispatch_called = True
                controller.dispatch()
        else:
            return action(*args, **kwargs)
    return decorate
