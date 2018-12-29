import base64
import json
import logging
import os
from datetime import timedelta

from tornado.httputil import HTTPServerRequest
import tornado.web
from webtest import TestApp

# from config.constants import SUPPORT_EMAIL

from base import BaseTestCase, UCHAR

# needed to log in properly
HEADERS = {'USER_AGENT': 'Test Python UA'}
ENVIRON = {'REMOTE_ADDR': '127.0.0.1'}


class BaseTestController(BaseTestCase):

    def setUp(self):
        super(BaseTestController, self).setUp()
        # this must be imported after the above setup in order for the stubs to work
        from main import app
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
        if response.status_int == 200:
            self.prior_response = response
        return response

    def sessionPost(self, *args, **kwargs):
        # properly sets cookies for the session to work so that it doesn't have to be done every time
        args = list(args) # convert from tuple so we can modify below
        data = args[1]

        data['_xsrf'] = self.getXsrf(args[0])
        args[1] = data

        response = self.app.post(*args, **kwargs)
        self.setCookie(response)
        return response

    def getXsrf(self, url):
        if hasattr(self, 'prior_response') and self.prior_response:
            response = self.prior_response
            self.prior_response = None
        else:
            response = self.app.get(url)
            assert response.status_int == 200
            self.setCookie(response)

        value_split = response.body.decode('utf8').split('name="_xsrf" value="', 1)[1]
        return value_split.split('"', 1)[0]

    def login(self, user=None):
        if not user and hasattr(self, "user"):
            user = self.user
        assert user, "A user is required to sign in."
        return self.sessionPost('/user/login', {'email': user.email.encode('utf8'),
            'password': user.password.encode('utf8')}, headers=HEADERS, extra_environ=ENVIRON)

    def logout(self):
        response = self.app.post('/user/logout', {'_xsrf': self.getXsrf('/home')})
        return response


class BaseMockController(BaseTestController):
    """ abstract base class for tests that need request, response, and session mocking """

    def getMockRequest(self):
        class MockConnection(object):
            def finish(self):
                pass

            def set_close_callback(self, callback):
                pass

            def write_headers(self, start_line, headers, chunk, callback=None):
                pass

        return HTTPServerRequest(uri='/test-path', connection=MockConnection())

    def mockSessions(self):
        # this is used by tests that want to bypass needing to perform session-dependent actions within a request
        self.controller.session = {}

    def mockLogin(self):
        self.auth = self.createAuth(self.user)
        self.controller.session["auth_key"] = self.auth.slug


class TestBase(BaseMockController):

    def setUp(self):
        super(TestBase, self).setUp()

        self.controller = self.controller_base.BaseController(
            self.app.app, self.getMockRequest()
        )

    def test_prepare(self):

        def before():
            self.called = True

        self.controller.before = before

        # before should be called if it exists
        self.called = False
        self.controller.prepare()
        assert self.called

        # if there is an error or redirect in before then the request should be finished
        self.controller.set_status(500)
        try:
            self.controller.prepare()
        except tornado.web.Finish:
            pass
        else:
            assert False

    def test_saveSession(self):

        # sessions can only be used during a request, so we prepare for one
        self.controller.prepare()

        def set_secure_cookie(name, data, **kwargs):
            self.name = name
            self.data = data

        self.name = self.data = None
        self.controller.set_secure_cookie = set_secure_cookie
        self.controller.session["test key"] = "test value" + UCHAR
        self.controller.saveSession()
        assert self.name == 'session'
        assert self.data == json.dumps({"test key": "test value" + UCHAR})

    def test_gcs_bucket(self):
        bucket = self.controller.gcs_bucket
        assert bucket == "test.appspot.com"

    def test_logger(self):
        logger = self.controller.logger
        assert logger

    def test_flash(self):
        self.mockSessions()
        self.controller.flash("info", "test flash" + UCHAR)
        assert self.controller.session.get("flash") == {"level": "info", "message": "test flash" + UCHAR}

    def test_compileTemplate(self):
        self.mockSessions()
        result = self.controller.compileTemplate('index.html')
        assert b'<h2>Index Page</h2>' in result

    def test_securityHeaders(self):
        assert not self.controller._headers.get('Content-Security-Policy')
        self.controller.securityHeaders()
        assert '/policyviolation' in self.controller._headers.get('Content-Security-Policy', '')

    def test_renderTemplate(self):
        self.mockSessions()
        self.controller.renderTemplate('index.html')
        assert self.controller._headers['Content-Type'] == "text/html; charset=UTF-8"
        found = False
        for part in self.controller._write_buffer:
            if b'<h2>Index Page</h2>' in part:
                found = True
                break
        assert found

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller._write_buffer = []
        self.controller.request.method = 'HEAD'
        self.controller.renderTemplate('index.html')
        assert self.controller._headers['Content-Type'] == "text/html; charset=UTF-8"
        assert not self.controller._write_buffer

    def test_renderError(self):
        self.mockSessions()
        self.controller.renderError(500)
        found = False
        for part in self.controller._write_buffer:
            if b"Error 500:" in part:
                found = True
                break
        assert found

    def test_renderJSON(self):
        self.mockSessions()
        data = {"test key": "test value" + UCHAR}
        self.controller.renderJSON(data)
        assert self.controller._headers['Content-Type'] == "application/json; charset=UTF-8"
        found = False
        for part in self.controller._write_buffer:
            if b'{"test key": "test value\\u03b4"}' in part:
                found = True
                break
        assert found

        # a HEAD request should not actually render anything, but the type should still be there
        self.controller._write_buffer = []
        self.controller.request.method = 'HEAD'
        self.controller.renderJSON(data)

        # note that charset is not set because no unicode was rendered
        assert self.controller._headers['Content-Type'] == "application/json"
        assert not self.controller._write_buffer

    def test_head(self):

        def get():
            self.called = True

        self.controller.get = get

        # HEAD should just call the GET version
        self.called = False
        self.controller.head()
        assert self.called

        # but not have a response body
        assert not self.controller._write_buffer

    def test_redirect(self):
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        self.controller.redirect('/test-redirect-url')

        assert self.controller.get_status() == 302
        assert "Location: /test-redirect-url" in str(self.controller._headers)

    def test_redisplay(self):
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        self.controller.redisplay("form_data", "errors", "/test-redirect-url")

        assert self.controller.session.get("form_data") == "form_data"
        assert self.controller.session.get("errors") == "errors"

        assert self.controller.get_status() == 302
        assert "Location: /test-redirect-url" in str(self.controller._headers)

    def test_write_error(self):
        self.mockSessions()
        # temporarily disable exception logging for this test to avoid messy printouts
        logging.disable(logging.CRITICAL)
        self.controller.write_error(500, False)
        logging.disable(logging.NOTSET)
        found = False
        for part in self.controller._write_buffer:
            if b"Error 500:" in part:
                found = True
                break
        assert found

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "A User Has Experienced an Error" in str(messages[0].html)

    def test_get_current_user(self):
        user = self.createUser()
        auth = self.createAuth(self.user)

        # need to hold on to the original (messes up other tests other wise)
        orig_cookie = self.controller.get_secure_cookie

        cookie = ''

        def get_secure_cookie(name):
            return cookie

        self.controller.get_secure_cookie = get_secure_cookie

        # to begin with the user should return nothing
        assert self.controller.current_user is None

        # if an invalid auth key is added it should still return none without errors
        cookie = b"99.99"

        # because of the way cached properties work we have to do a little hack to re-evaluate
        self.controller.current_user = self.controller.get_current_user()

        assert self.controller.current_user is None

        # finally if a valid keys is added to the session it should return the user object
        cookie = auth.slug.encode() # needs to be bytes, not string
        self.controller.current_user = self.controller.get_current_user()

        assert self.controller.current_user is not None
        assert self.controller.current_user.key == user.key

        self.controller.get_secure_cookie = orig_cookie

    def test_deferEmail(self):
        to = 'test' + UCHAR + '@example.com'
        subject = 'Subject' + UCHAR
        # html = '<p>A User Has Experienced an Error</p>'
        self.controller.deferEmail([to], subject, 'error_alert.html', user=None, url='', method='', message='')

        # move mails out of the queue so we can test them
        # self.executeDeferred(name='mail')
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == to
        # assert messages[0].subject == subject
        #
        # having a unicode char triggers base64 encoding
        # assert html.encode('utf-8').encode('base64') in str(messages[0].html)
        # assert not hasattr(messages[0], 'reply_to')

        reply_to = 'test.reply' + UCHAR + '@example.com'
        content = b'content'
        cid = 'content-id'
        filename = 'file.ext'
        attachments = [{'content': content, 'content_id': cid, 'filename': filename, 'type': 'mime/type'}]
        self.controller.deferEmail([to], subject, 'error_alert.html', attachments=attachments, reply_to=reply_to,
            user=None, url='', method='', message='')

        # self.executeDeferred(name='mail')
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 2
        # assert hasattr(messages[1], 'reply_to')
        # assert messages[1].reply_to == reply_to
        #
        # original = str(messages[1].original)
        # assert content.encode('base64') in original
        # assert cid in original
        # assert filename in original


class TestForm(BaseMockController):

    def setUp(self):
        super(TestForm, self).setUp()

        self.controller = self.controller_base.FormController(
            self.app.app, self.getMockRequest()
        )

    def test_validate(self):
        # NOTE: internally any value is an iterable, so we make them lists here to match
        arguments = {"valid_field": ["value" + UCHAR], "invalid_field": ["value" + UCHAR]}
        self.controller.request.arguments = arguments
        self.controller.FIELDS = {"valid_field": lambda x: (True, x + "valid"), "invalid_field": lambda x: (False, "")}
        form_data, errors, valid_data = self.controller.validate()

        assert form_data["valid_field"] == arguments["valid_field"][0]
        assert form_data["invalid_field"] == arguments["invalid_field"][0]
        assert errors == {"invalid_field": True}
        assert valid_data == {"valid_field": "value" + UCHAR + "valid"}

        # non-utf8 should result in a bad request
        self.controller.request.arguments = {"valid_field": [b"\xff"]}
        try:
            self.controller.validate()
        except tornado.web.HTTPError as e:
            assert e.status_code == 400
        else:
            assert False


class TestDecorators(BaseMockController):

    def setUp(self):
        super(TestDecorators, self).setUp()

        self.controller = self.controller_base.BaseController(
            self.app.app, self.getMockRequest()
        )

    def test_withoutUser(self):
        self.mockSessions()
        self.createUser()
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        def action(x):
            return 'action'

        decorator = self.controller_base.withoutUser(action)

        # without a user the action should complete without a redirect
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 302

        # with a user the action should not complete and it should redirect
        self.mockLogin()
        self.controller.current_user = self.user
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 302
        assert "Location: /home" in str(self.controller._headers)

    def test_removeSlash(self):
        self.controller.prepare()
        self.controller._transforms = [] # normally done in execute, so we have to do it manually

        def action(x):
            return 'action'

        decorator = self.controller_base.removeSlash(action)

        # without a slash it should not redirect
        self.controller.request.path = "/no-slash"
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 301

        # with a slash it should
        self.controller.request.path = "/with-slash/"
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 301
        assert "Location: /with-slash" in str(self.controller._headers)

    def test_validateReferer(self):
        self.mockSessions()
        self.controller.prepare()

        def action(x):
            return 'action'

        decorator = self.controller_base.validateReferer(action)

        # with a valid referer the action should complete
        self.controller.request.headers = {"referer": "http://valid", "host": "valid"}
        response = decorator(self.controller)
        assert response == "action"
        assert self.controller.get_status() != 400

        # without a valid referer the request should not go through
        self.controller.request.headers = {"referer": "invalid", "host": "valid"}
        response = decorator(self.controller)
        assert response != "action"
        assert self.controller.get_status() == 400


class TestError(BaseTestController):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        logging.disable(logging.CRITICAL)
        assert self.app.get('/nothing-to-see-here', status=404)
        logging.disable(logging.NOTSET)

    def test_logError(self):
        # static error pages call this to log to try to log themselves
        logging.disable(logging.CRITICAL)
        assert self.app.post('/logerror', {'reason': 'Default'}, status=200)
        logging.disable(logging.NOTSET)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "Error Message: Static Error Page: Default" in str(messages[0].html)

        # javascript errors also call this to log errors
        logging.disable(logging.CRITICAL)
        assert self.app.post('/logerror', {'javascript': 'error'}, status=200)
        logging.disable(logging.NOTSET)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 2
        # assert messages[1].to == SUPPORT_EMAIL
        # assert messages[1].subject == "Error Alert"
        # assert "Error Message: JavaScript Error: error" in str(messages[1].html)

    def test_policyViolation(self):
        # csp violations are reported directly from browsers
        logging.disable(logging.CRITICAL)
        assert self.app.post('/policyviolation', 'CSP JSON', status=200)
        logging.disable(logging.NOTSET)

        # move mails out of the queue so we can test them
        # self.executeDeferred(name="mail")
        #
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == SUPPORT_EMAIL
        # assert messages[0].subject == "Error Alert"
        # assert "Error Message: Content Security Policy Violation: CSP JSON" in str(messages[0].html)


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
        assert b'<h2>Logged In Home Page</h2>' in response


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
        assert 'alt="Profile Pic"' not in response

        # test upload - upload_files doesn't actually seem to work, so we test what we can
        upload_files = [("profile_pic", "profile.jpg", b"file content", "")]
        response = self.sessionPost('/user', {}, upload_files=upload_files)
        response = response.follow()
        assert '<h2>Account Settings</h2>' in response

        # test delete
        response = self.sessionPost('/user', {'delete': '1'})
        response = response.follow()
        assert '<h2>Account Settings</h2>' in response

    def test_auths(self):
        self.login()

        user_auth = list(self.user.auths)[0]

        response = self.app.get('/user/auths')
        assert '<h2>Active Sessions</h2>' in response
        assert user_auth.slug not in response
        assert user_auth.modified_dt.isoformat() in response
        assert 'Current Session' in response

        data = {'auth_key': ''}
        response = self.sessionPost('/user/auths', data, status=302)

        # test that the user is not allowed to remove another's auth
        data['auth_key'] = self.other_auth.slug

        logging.disable(logging.CRITICAL)
        assert self.sessionPost('/user/auths', data, status=403)
        logging.disable(logging.NOTSET)

        data['auth_key'] = user_auth.slug
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
        logging.disable(logging.CRITICAL)
        assert self.app.get('/user/logout', status=405)
        logging.disable(logging.NOTSET)

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
        # self.executeDeferred(name="mail")
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 0

        # an email address that is associated with a user should respond the same
        data = {"email": self.user.email.encode("utf8")}
        response = self.sessionPost('/user/forgotpassword', data)
        response = response.follow()
        assert 'Your password reset email has been sent.' in response

        # except this time the mail queue should have something
        # self.executeDeferred(name="mail")
        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to == self.user.email
        # assert messages[0].subject == "Reset Password"

    def test_resetPassword(self):
        key = self.user.slug

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
        response = self.sessionGet('/user/resetpassword?key=' + key + '&token=' + token)
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

        # generate a new xsrf after the successful post above
        self.sessionGet('/user/resetpassword?key=' + key + '&token=' + self.user.token)

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
        self.user.update(token_dt=self.user.token_dt - timedelta(seconds=3600))
        self.user.put()
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

        logging.disable(logging.CRITICAL)
        assert self.app.get('/admin', status=403)
        logging.disable(logging.NOTSET)

        self.logout()
        self.login(self.admin_user)

        response = self.app.get('/admin')
        assert '<h2>Admin</h2>' in response


class TestAPI(BaseTestController):

    def setUp(self):
        super(TestAPI, self).setUp()
        self.createUser()

    def test_upload(self):
        self.login()

        # get a page first so the XSRF is generated (no get action for api)
        self.sessionGet('/user')

        response = self.sessionPost('/api/upload', {'url': '/user'})
        assert 'url' in response


class TestDev(BaseTestController):

    def test_dev(self):
        response = self.app.get('/dev')
        assert '<h2>Dev</h2>' in response

        # test clearing memcache out
        response = self.sessionPost('/dev', {"memcache": "1"})
        assert response.status_int == 302


class TestJob(BaseTestController):

    def test_auths(self):
        response = self.app.get('/job/auths')
        assert 'OK' in response

    def test_email(self):
        data = {
            'to': ('test' + UCHAR + '@example.com').encode('utf-8'),
            'subject': ('Subject' + UCHAR).encode('utf-8'),
            'html': ('<p>Test body' + UCHAR + '</p>').encode('utf-8')
        }
        self.app.post('/job/email', data)

        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 1
        # assert messages[0].to.encode('utf-8') == data['to']
        # assert messages[0].subject.encode('utf-8') == data['subject']
        # # having a unicode char triggers base64 encoding
        # assert data['html'].encode('base64') in str(messages[0].html)
        # assert ('Test body' + UCHAR).encode('utf-8').encode('base64') in str(messages[0].body)
        # assert not hasattr(messages[0], 'reply_to')

        content = base64.b64encode(b'content').decode()
        cid = 'content-id'
        filename = 'file.ext'
        attachments = [{'content': content, 'content_id': cid, 'filename': filename, 'type': 'mime/type'}]
        data['attachments'] = json.dumps(attachments)
        data['reply_to'] = ('test.reply' + UCHAR + '@example.com').encode('utf-8')
        self.app.post('/job/email', data)

        # messages = self.mail_stub.get_sent_messages()
        # assert len(messages) == 2
        # assert hasattr(messages[1], 'reply_to')
        # assert messages[1].reply_to.encode('utf-8') == data['reply_to']
        #
        # original = str(messages[1].original)
        # assert content in original
        # assert cid in original
        # assert filename in original
