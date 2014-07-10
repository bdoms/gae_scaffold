import os

from webtest import TestApp

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

    def test_dispatch(self):
        pass

    def test_session(self):
        pass

    def test_flash(self):
        pass

    def test_cacheAndRenderTemplate(self):
        pass

    def test_compileTemplate(self):
        pass

    def test_renderTemplate(self):
        pass

    def test_renderError(self):
        pass

    def test_renderJSON(self):
        pass

    def test_handle_exception(self):
        pass

    def test_cache(self):
        pass

    def test_uncache(self):
        pass

    def test_user(self):
        pass


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
