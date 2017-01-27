import logging
import os
from datetime import timedelta

import jinja2

from webtest import TestApp

from config.constants import SUPPORT_EMAIL

from base import BaseTestCase, UCHAR

# needed to log in properly
HEADERS = {'USER_AGENT': 'Test Python UA'}
ENVIRON = {'REMOTE_ADDR': '127.0.0.1'}


class BaseTestController(BaseTestCase):

    def setUp(self):
        super(BaseTestController, self).setUp()
        # this must be imported after the above setup in order for the stubs to work
        from website import app
        from controllers import base as controller_base
        self.app = TestApp(app)
        self.controller_base = controller_base

    def setCookie(self, response):
        if 'Set-Cookie' in response.headers:
            cookies = response.headers.getall('Set-Cookie')
            os.environ['HTTP_COOKIE'] = " ".join(cookies)

    def sessionGet(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        response = self.app.get(*args, **kwargs)
        self.setCookie(response)
        return response

    def sessionPost(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        response = self.app.post(*args, **kwargs)
        self.setCookie(response)
        return response

    def login(self, user=None):
        if not user and hasattr(self, "user"):
            user = self.user
        assert user, "A user is required to sign in."
        return self.sessionPost('/user/login', {'email': user.email.encode('utf8'),
            'password': user.password.encode('utf8')}, headers=HEADERS, extra_environ=ENVIRON)

    def logout(self):
        response = self.app.post('/user/logout')
        return response


class BaseMockController(BaseTestController):
    """ abstract base class for tests that need request, response, and session mocking """

    def getMockRequest(self, request_method="get"):
        # calling straight into the controller without a route requires some mock objects to work
        class MockRequest(self.app.app.request_class):
            class MockRoute(object):
                handler_method = request_method
            app = self.app.app
            method = request_method
            path = url = "/test-path"
            host_url = "http://localhost"
            query_string = "test=query"
            headers = route_args = route_kwargs = {}
            route = MockRoute()
        return MockRequest({})

    def mockSessions(self):
        # this is used by tests that want to bypass needing to perform session-dependent actions within a request
        class MockSessionStore(object):
            def get_session(self): return {}
        self.controller.session_store = MockSessionStore()

    def mockLogin(self):
        self.auth = self.createAuth(self.user)
        self.controller.session["auth_key"] = self.auth.key.urlsafe()


class TestBase(BaseMockController):

    def setUp(self):
        super(TestBase, self).setUp()

        self.controller = self.controller_base.BaseController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

    def test_dispatch(self):
        
        def before(): self.call_list.append("before")
        def get(): self.call_list.append("get")
        def after(): self.call_list.append("after")
        self.controller.before = before
        self.controller.get = get
        self.controller.after = after

        # in a normal request before, the action, and after should all be called in order
        self.call_list = []
        self.controller.dispatch()
        assert self.call_list == ["before", "get", "after"]

        # if there is an error or redirect in before then the action and after should not be called
        self.call_list = []
        self.controller.response.set_status(500)
        self.controller.dispatch()
        assert self.call_list == ["before"]

    def test_session(self):
        # sessions can only be used during a request, so we create a mock one to save something
        def get(): self.controller.session["test key"] = "test value" + UCHAR
        self.controller.get = get
        self.controller.dispatch()
        assert self.controller.session.get("test key") == "test value" + UCHAR

    def test_flash(self):
        self.mockSessions()
        self.controller.flash("info", "test flash" + UCHAR)
        assert self.controller.session.get("flash") == {"level": "info", "message": "test flash" + UCHAR}

    def test_compileTemplate(self):
        self.mockSessions()
        template = jinja2.Template("test compile template" + UCHAR)
        result = self.controller.compileTemplate(template)
        assert "test compile template" + UCHAR in result

    def test_renderTemplate(self):
        self.mockSessions()
        template = jinja2.Template("test render template" + UCHAR)
        self.controller.renderTemplate(template)
        assert self.controller.response.headers['Content-Type'] == "text/html; charset=utf-8"
        assert "test render template" + UCHAR in self.controller.response.unicode_body

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller.initialize(self.getMockRequest(request_method="HEAD"), self.app.app.response_class())
        self.controller.renderTemplate(template)
        assert self.controller.response.headers['Content-Type'] == "text/html; charset=utf-8"
        assert not self.controller.response.unicode_body

    def test_renderError(self):
        self.mockSessions()
        self.controller.renderError(500)
        assert "Error 500:" in self.controller.response.body

    def test_renderJSON(self):
        data = {"test key": "test value" + UCHAR}
        self.controller.renderJSON(data)
        assert self.controller.response.headers['Content-Type'] == "application/json; charset=utf-8"
        assert self.controller.response.unicode_body == '{"test key": "test value' + UCHAR + '"}'

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller.initialize(self.getMockRequest(request_method="HEAD"), self.app.app.response_class())
        self.controller.renderJSON(data)

        # note that charset is not set because no unicode was rendered
        assert self.controller.response.headers['Content-Type'] == "application/json"
        assert not self.controller.response.body

    def test_head(self):
        def get(): self.called = True
        self.controller.get = get

        # HEAD should just call the GET version
        self.called = False
        self.controller.head()
        assert self.called

        # but not have a response body
        assert not self.controller.response.unicode_body
        assert not self.controller.response.body

    def test_handle_exception(self):
        self.mockSessions()
        # temporarily disable exception logging for this test to avoid messy printouts
        logging.disable(logging.CRITICAL)
        self.controller.handle_exception("test exception", False)
        logging.disable(logging.NOTSET)
        assert "Error 500:" in self.controller.response.body

        # move mails out of the queue so we can test them
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == SUPPORT_EMAIL
        assert messages[0].subject == "Error Alert"
        assert "A User Has Experienced an Error" in str(messages[0].html)

    def test_cache(self):
        self.executed = 0
        def testFunction():
            self.executed += 1
            return "test value"
        assert self.executed == 0

        result = self.controller.cache("test key", testFunction)
        assert result == "test value"
        assert self.executed == 1

        # the value should now be cached, so the function should not be executed again
        result = self.controller.cache("test key", testFunction)
        assert self.executed == 1

    def test_uncache(self):
        from google.appengine.api import memcache

        # confirm the key exists when it is added
        memcache.set("test key", "test value")
        assert memcache.get("test key") == "test value"

        # and that it's gone when removed
        self.controller.uncache("test key")
        assert memcache.get("test key") is None

    def test_user(self):
        self.mockSessions()
        user = self.createUser()

        # to begin with the user should return nothing
        assert self.controller.user is None

        # if an invalid auth key is added it should still return none without errors
        self.controller.session["auth_key"] = "doesn't exist"

        # because of the way cached properties work we have to do a little hack to re-evaluate
        self.controller.user = self.controller_base.BaseController.user.func(self.controller)

        assert self.controller.user is None

        # finally if a valid keys is added to the session it should return the user object
        self.mockLogin()
        self.controller.user = self.controller_base.BaseController.user.func(self.controller)
        
        assert self.controller.user is not None
        assert self.controller.user.key == user.key

    def test_sendEmail(self):
        to = "test" + UCHAR + "@example.com"
        subject = "Subject" + UCHAR
        html = "<p>Test body</p>"
        self.controller.sendEmail([to], subject, html)

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == to
        assert messages[0].subject == subject
        assert html in str(messages[0].html)
        assert "Test body" in str(messages[0].body)
        assert "<p>" not in str(messages[0].body)
        assert not hasattr(messages[0], "reply_to")

        reply_to = "test_reply" + UCHAR + "@example.com"
        self.controller.sendEmail([to], subject, html, reply_to)
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 2
        assert messages[1].reply_to == reply_to

    def test_deferEmail(self):
        to = "test" + UCHAR + "@example.com"
        subject = "Subject" + UCHAR
        html = "<p>test email template</p>"
        template = jinja2.Template(html)
        self.controller.deferEmail([to], subject, template)

        # move mails out of the queue so we can test them
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == to
        assert messages[0].subject == subject
        assert html in str(messages[0].html)


class TestForm(BaseMockController):

    class UnicodeMockRequest(object):
        method = "POST"
        def __init__(self, d):
            self.d = d
        def get(self, field):
            return unicode(self.d.get(field))

    def setUp(self):
        super(TestForm, self).setUp()

        self.controller = self.controller_base.FormController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

    def test_validate(self):
        self.controller.request = {"valid_field": "value" + UCHAR, "invalid_field": "value" + UCHAR}
        self.controller.FIELDS = {"valid_field": lambda x: (True, x + "valid"), "invalid_field": lambda x: (False, "")}
        form_data, errors, valid_data = self.controller.validate()

        assert form_data == self.controller.request
        assert errors == {"invalid_field": True}
        assert valid_data == {"valid_field": "value" + UCHAR + "valid"}

        # non-utf8 should result in a bad request
        self.mockSessions()
        self.controller.request = self.UnicodeMockRequest({"valid_field": "\xff"})
        self.controller.validate()
        assert self.controller.response.status_int == 400

    def test_redisplay(self):
        self.mockSessions()

        self.controller.redisplay("form_data", "errors", "/test-redirect-url")

        assert self.controller.session.get("form_data") == "form_data"
        assert self.controller.session.get("errors") == "errors"

        assert self.controller.response.status_int == 302
        assert "Location: /test-redirect-url" in str(self.controller.response.headers)


class TestDecorators(BaseMockController):

    def setUp(self):
        super(TestDecorators, self).setUp()

        self.controller = self.controller_base.BaseController()
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

    def test_withUser(self):
        self.mockSessions()
        self.createUser()

        action = lambda x: "action"
        decorator = self.controller_base.withUser(action)

        # without a user the action should not be performed and it should redirect
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.response.status_int == 302
        assert "Location: /user/login" in str(self.controller.response.headers)

        # re-init to clear old response
        self.controller.initialize(self.getMockRequest(), self.app.app.response_class())

        # login user
        self.mockLogin()
        self.controller.user = self.controller_base.BaseController.user.func(self.controller)

        # with a user the action should complete without a redirect
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.response.status_int != 302

    def test_withoutUser(self):
        self.mockSessions()
        self.createUser()

        action = lambda x: "action"
        decorator = self.controller_base.withoutUser(action)

        # without a user the action should complete without a redirect
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.response.status_int != 302

        # with a user the action should not complete and it should redirect
        self.mockLogin()
        self.controller.user = self.controller_base.BaseController.user.func(self.controller)
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.response.status_int == 302
        assert "Location: /home" in str(self.controller.response.headers)

    def test_removeSlash(self):
        action = lambda x: "action"
        decorator = self.controller_base.removeSlash(action)

        # without a slash it should not redirect
        self.controller.request.path = "/no-slash"
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.response.status_int != 301

        # with a slash it should
        self.controller.request.path = "/with-slash/"
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.response.status_int == 301
        assert "Location: /with-slash" in str(self.controller.response.headers)

    def test_validateReferer(self):
        self.mockSessions()
        action = lambda x: "action"
        decorator = self.controller_base.validateReferer(action)

        # with a valid referer the action should complete
        self.controller.request.headers = {"referer": "http://valid", "host": "valid"}
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.response.status_int != 400

        # without a valid referer the request should not go through
        self.controller.request.headers = {"referer": "invalid", "host": "valid"}
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.response.status_int == 400


class TestError(BaseTestController):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        assert self.app.get('/nothing-to-see-here', status=404)

    def test_logError(self):
        # static error pages call this to log to try to log themselves
        logging.disable(logging.CRITICAL)
        assert self.app.post('/logerror', {'reason': 'Default'}, status=200)
        logging.disable(logging.NOTSET)

        # move mails out of the queue so we can test them
        self.executeDeferred(name="mail")

        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == SUPPORT_EMAIL
        assert messages[0].subject == "Error Alert"
        assert "Error Message: Static Error Page: Default" in str(messages[0].html)


class TestIndex(BaseTestController):

    def test_index(self):
        response = self.app.get('/')
        assert '<h2>Index Page</h2>' in response


class TestHome(BaseTestController):

    def setUp(self):
        super(TestHome, self).setUp()
        self.createUser()
        self.login()

    def test_home(self):
        response = self.app.get('/home')
        assert '<h2>Logged In Home Page</h2>' in response


class TestSitemap(BaseTestController):

    def test_sitemap(self):
        response = self.app.get('/sitemap.xml')
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in response


class TestStatic(BaseTestController):

    def test_static(self):
        # loop through and test every known static page
        pages = {'/terms': 'Terms of Service', '/privacy': 'Privacy Policy'}
        for page in pages:
            response = self.app.get(page)
            assert "<h2>" + pages[page] + "</h2>" in response, pages[page] + " not found"


class TestUser(BaseTestController):

    def setUp(self):
        super(TestUser, self).setUp()
        self.createUser()
        self.other_user = self.createUser(email='test2@test.com')
        self.other_auth = self.createAuth(user=self.other_user)

    def test_index(self):
        self.login()

        response = self.app.get('/user')
        assert '<h2>Account Settings</h2>' in response

    def test_auths(self):
        self.login()

        user_auth = list(self.user.auths)[0]

        response = self.app.get('/user/auths')
        assert '<h2>Active Sessions</h2>' in response
        assert user_auth.last_login.isoformat() in response
        assert user_auth.key.urlsafe() not in response
        assert 'Current Session' in response

        data = {'auth_key': 'invalid'}

        response = self.sessionPost('/user/auths', data)
        response = response.follow()
        assert 'Invalid session.' in response
        assert '<h2>Active Sessions</h2>' in response

        # test that the user is not allowed to remove another's auth
        data['auth_key'] = self.other_auth.key.urlsafe()
        assert self.sessionPost('/user/auths', data, status=403)

        data['auth_key'] = user_auth.key.urlsafe()
        response = self.sessionPost('/user/auths', data)
        response = response.follow()
        response = response.follow() # we revoked our own session, so it redirects twice
        assert 'Access revoked.' in response
        assert '<h2>Log In</h2>' in response

    def test_changeEmail(self):
        self.login()

        response = self.app.get('/user/email')
        assert '<h2>Change Email</h2>' in response

        data = {}
        data["email"] = self.user.email.encode("utf8")
        data["password"] = "wrong password"

        response = self.sessionPost('/user/email', data)
        response = response.follow()
        assert 'Invalid current password.' in response

        data["password"] = self.user.password.encode("utf8")
        response = self.sessionPost('/user/email', data)
        response = response.follow()
        assert 'That email address is already in use.' in response

        data["email"] = ("changeemail.test" + UCHAR + "@example.com").encode("utf8")
        response = self.sessionPost('/user/email', data)
        response = response.follow()
        assert 'Email changed successfully.' in response

    def test_changePassword(self):
        self.login()

        response = self.app.get('/user/password')
        assert '<h2>Change Password</h2>' in response

        data = {}
        data["new_password"] = ("Test change password" + UCHAR).encode("utf8")
        data["password"] = "wrong password"

        response = self.sessionPost('/user/password', data)
        response = response.follow()
        assert 'Invalid current password.' in response

        data["password"] = self.user.password.encode("utf8")
        response = self.sessionPost('/user/password', data)
        response = response.follow()
        assert 'Password changed successfully.' in response

    def test_signup(self):
        response = self.app.get('/user/signup')
        assert '<h2>Sign Up</h2>' in response

        data = {}
        data["first_name"] = ("Test first name" + UCHAR).encode("utf8")
        data["last_name"] = ("Test last name" + UCHAR).encode("utf8")
        data["email"] = self.user.email.encode("utf8")
        data["password"] = ("Test password" + UCHAR).encode("utf8")

        response = self.sessionPost('/user/signup', data)
        response = response.follow()
        assert 'That email address is already in use.' in response

        # signup succeeds but won't login without valid user agent or IP address
        data["email"] = ("signup.test" + UCHAR + "@example.com").encode("utf8")

        response = self.sessionPost('/user/signup', data)
        response = response.follow()
        assert 'Invalid client.' in response

        # success - use a new email address to avoid conflict with the previous partial success
        data["email"] = ("signup2.test" + UCHAR + "@example.com").encode("utf8")

        response = self.sessionPost('/user/signup', data, headers=HEADERS, extra_environ=ENVIRON)
        response = response.follow()
        assert '<h2>Logged In Home Page</h2>' in response

    def test_login(self):
        response = self.app.get('/user/login')
        assert '<h2>Log In</h2>' in response

        # using an email address not associated with a user should fail silently
        data = {}
        data["email"] = ("doesnt.exist" + UCHAR + "@example.com").encode("utf8")
        data["password"] = "wrong password"

        response = self.sessionPost('/user/login', data)
        response = response.follow()
        assert 'Email and password do not match.' in response

        # a wrong password should also not succeed, even when the email exists
        data["email"] = self.user.email.encode("utf8")

        response = self.sessionPost('/user/login', data)
        response = response.follow()
        assert 'Email and password do not match.' in response

        # login fails without a user agent or IP address even when password is correct
        data["password"] = self.user.password.encode("utf8")

        response = self.sessionPost('/user/login', data)
        response = response.follow()
        assert 'Invalid client.' in response

        # success
        response = self.sessionPost('/user/login', data, headers=HEADERS, extra_environ=ENVIRON)
        response = response.follow() # redirects to home page
        assert '<h2>Logged In Home Page</h2>' in response

    def test_logout(self):
        self.login()

        # should not allow logging out via GET
        assert self.app.get('/user/logout', status=405)

        response = self.logout()
        response = response.follow() # redirects to index page
        assert '<h2>Index Page</h2>' in response

    def test_forgotPassword(self):
        response = self.app.get('/user/forgotpassword')
        assert '<h2>Forget Your Password?</h2>' in response

        # using an email address not associated with a user should fail silently
        data = {"email": ("doesnt.exist" + UCHAR + "@example.com").encode("utf8")}
        response = self.sessionPost('/user/forgotpassword', data)
        response = response.follow()
        assert 'Your password reset email has been sent.' in response

        # but the mail queue should be empty
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 0

        # an email address that is associated with a user should respond the same
        data = {"email": self.user.email.encode("utf8")}
        response = self.sessionPost('/user/forgotpassword', data)
        response = response.follow()
        assert 'Your password reset email has been sent.' in response

        # except this time the mail queue should have something
        self.executeDeferred(name="mail")
        messages = self.mail_stub.get_sent_messages()
        assert len(messages) == 1
        assert messages[0].to == self.user.email
        assert messages[0].subject == "Reset Password"

    def test_resetPassword(self):
        key = self.user.key.urlsafe()

        # without the right authorization this page should redirect with a warning
        response = self.app.get('/user/resetpassword')
        response = response.follow()
        assert 'That reset password link has expired.' in response

        # even if the user is found the token needs to be right
        response = self.app.get('/user/resetpassword?key=' + key + '&token=wrong')
        response = response.follow()
        assert 'That reset password link has expired.' in response

        # with the right auth this page should display properly
        self.user = self.user.resetPassword()
        token = self.user.token
        response = self.app.get('/user/resetpassword?key=' + key + '&token=' + token)
        assert '<h2>Reset Password</h2>' in response

        # posting a new password but without user agent or IP address won't log in
        new_password = "Test password2" + UCHAR
        data = {}
        data["password"] = new_password.encode("utf8")
        data["key"] = key
        data["token"] = token

        response = self.sessionPost('/user/resetpassword', data)
        response = response.follow()
        assert 'Invalid client.' in response

        # posting a new password should log the user in - reset again to get a new token
        self.user = self.user.resetPassword()
        data["token"] = self.user.token

        response = self.sessionPost('/user/resetpassword', data, headers=HEADERS, extra_environ=ENVIRON)
        response = response.follow()
        assert '<h2>Logged In Home Page</h2>' in response

        # should be able to log in with the new password now too
        self.logout()
        self.user.password = new_password
        response = self.login()
        response = response.follow()
        assert '<h2>Logged In Home Page</h2>' in response

        # test that we can't reset a second time
        self.logout()
        response = self.app.get('/user/resetpassword?key=' + key + '&token=' + token)
        response = response.follow()
        assert 'That reset password link has expired.' in response

        # test that an expired token actually fails
        self.user = self.user.resetPassword()
        token = self.user.token
        
        # works the first time
        response = self.app.get('/user/resetpassword?key=' + key + '&token=' + token)
        assert '<h2>Reset Password</h2>' in response

        # fails when we move back the date
        self.user.token_date -= timedelta(seconds=3600)
        response = self.app.get('/user/resetpassword?key=' + key + '&token=' + token)
        response = response.follow()
        assert 'That reset password link has expired.' in response


class TestAdmin(BaseTestController):

    def setUp(self):
        super(TestAdmin, self).setUp()
        self.normal_user = self.createUser()
        self.admin_user = self.createUser(email="admin.test@example.com", is_admin=True)

    def test_admin(self):
        self.login(self.normal_user)

        assert self.app.get('/admin', status=403)

        self.logout()
        self.login(self.admin_user)

        response = self.app.get('/admin')
        assert '<h2>Admin</h2>' in response


class TestDev(BaseTestController):

    def test_dev(self):
        response = self.app.get('/dev')
        assert '<h2>Dev</h2>' in response

        # test clearing memcache out
        response = self.app.post('/dev', {"memcache": "1"})
        assert response.status_int == 302
