import logging
import os

import jinja2

from webtest import TestApp

from controllers import base as controller_base

from base import BaseTestCase, UCHAR


class BaseTestController(BaseTestCase):

    def setUp(self):
        super(BaseTestController, self).setUp()
        # this must be imported after the above setup in order for the stubs to work
        from website import app
        self.app = TestApp(app)

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
        return self.sessionPost('/login', {'email': user.email.encode('utf8'), 'password': user.password.encode('utf8')})

    def logout(self):
        response = self.app.get('/logout')
        return response


class TestBase(BaseTestController):

    def setUp(self):
        super(TestBase, self).setUp()
        
        # we're calling straight into the base controller without a route so it needs some mock objects
        class mockRoute(object):
            handler_method = "get"
        class mockRequest(self.app.app.request_class):
            app = self.app.app
            path = "/test-path"
            query_string = "test=query"
            route_args = {}
            route_kwargs = {}
            route = mockRoute()

        self.controller = controller_base.BaseController()
        self.controller.initialize(mockRequest({}), self.app.app.response_class())

    def mockSessions(self):
        # this is used by tests that want to bypass needing to perform session-dependent actions within a request
        class mockStore(object):
            def get_session(self): return {}
        self.controller.session_store = mockStore()

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

    def test_cacheAndRenderTemplate(self):
        self.mockSessions()
        # using a template object directly means that we don't need to use the file system
        template = jinja2.Template("test cache and render template" + UCHAR)
        self.controller.cacheAndRenderTemplate(template)
        assert "test cache and render template" + UCHAR in self.controller.response.unicode_body

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

    def test_renderError(self):
        self.mockSessions()
        self.controller.renderError(500)
        assert "Error 500:" in self.controller.response.body

    def test_renderJSON(self):
        self.controller.renderJSON({"test key": "test value" + UCHAR})
        assert self.controller.response.headers['Content-Type'] == "application/json; charset=utf-8"
        assert self.controller.response.unicode_body == '{"test key": "test value' + UCHAR + '"}'

    def test_handle_exception(self):
        self.mockSessions()
        # temporarily disable exception logging for this test to avoid messy printouts
        logging.disable(logging.CRITICAL)
        self.controller.handle_exception("test exception", False)
        logging.disable(logging.NOTSET)
        assert "Error 500:" in self.controller.response.body

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

        # if an invalid user key is added it should still return none without errors
        self.controller.session["user_key"] = "doesn't exist"

        # because of the way cached properties work we have to do a little hack to re-evaluate
        self.controller.user = controller_base.BaseController.user.func(self.controller)

        assert self.controller.user is None

        # if a valid user key is added but without valid authorization it should still return none
        self.controller.session["user_key"] = user.key.urlsafe()
        self.controller.session["user_auth"] = "bad auth"
        self.controller.user = controller_base.BaseController.user.func(self.controller)

        assert self.controller.user is None

        # finally if both valid keys are added to the session it should return the user object
        self.controller.session["user_key"] = user.key.urlsafe()
        self.controller.session["user_auth"] = user.getAuth()
        self.controller.user = controller_base.BaseController.user.func(self.controller)
        
        assert self.controller.user is not None
        assert self.controller.user.key == user.key


class TestForm(BaseTestController):

    def test_validate(self):
        pass

    def test_redisplay(self):
        pass


class TestValidators(BaseTestController):

    def test_withUser(self):
        pass

    def test_withoutUser(self):
        pass

    def test_removeSlash(self):
        pass

    def test_validateReferer(self):
        pass


class TestError(BaseTestController):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        assert self.app.get('/nothing-to-see-here', status=404)


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

    def test_signup(self):
        response = self.app.get('/signup')
        assert '<h2>Sign Up</h2>' in response

        data = {}
        data["first_name"] = ("Test first name" + UCHAR).encode("utf8")
        data["last_name"] = ("Test last name" + UCHAR).encode("utf8")
        data["email"] = ("signup.test" + UCHAR + "@example.com").encode("utf8")
        data["password"] = ("Test password" + UCHAR).encode("utf8")

        response = self.sessionPost('/signup', data)
        response = response.follow()
        assert '<h2>Logged In Home Page</h2>' in response

    def test_login(self):
        response = self.app.get('/login')
        assert '<h2>Log In</h2>' in response

        response = self.login()
        response = response.follow() # redirects to home page
        assert '<h2>Logged In Home Page</h2>' in response

    def test_logout(self):
        self.login()

        response = self.logout()
        response = response.follow() # redirects to index page
        assert '<h2>Index Page</h2>' in response


class TestAdmin(BaseTestController):

    def setUp(self):
        super(TestAdmin, self).setUp()
        self.createUser(is_admin=True)
        self.login()

    def test_admin(self):
        response = self.app.get('/admin')
        assert '<h2>Admin</h2>' in response


class TestDev(BaseTestController):

    def test_dev(self):
        response = self.app.get('/dev')
        assert '<h2>Dev</h2>' in response

        # test clearing memcache out
        response = self.app.post('/dev', {"memcache": "1"})
        assert response.status_int == 302
