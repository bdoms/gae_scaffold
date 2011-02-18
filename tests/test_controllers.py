from HTMLParser import HTMLParseError
from unittest import TestCase
from webtest import TestApp


class TestBase(TestCase):
    def setUp(self):
        # this must be done later to avoid a NoseGAE import bug (their issue #32)
        from website import application
        self.app = TestApp(application())

    def tearDown(self):
        pass

    def minify(self, response):
        # importing this outside of the function somehow makes it take over and try to minify everything
        from lib.gae_html.htmlmin import HTMLMinifier
        result = True
        minifier = HTMLMinifier()
        try:
            minifier.feed(str(response))
        except HTMLParseError:
            result = False
        minifier.close()
        return result


class TestError(TestBase):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        assert self.app.get('/nothing-to-see-here', status=404)


class TestIndex(TestBase):

    def test_index(self):
        response = self.app.get('/')
        assert '<h2>Index Page</h2>' in response
        assert self.minify(response)


class TestSitemap(TestBase):

    def test_sitemap(self):
        response = self.app.get('/sitemap.xml')
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in response
        assert self.minify(response)


class TestStatic(TestBase):

    def test_static(self):
        # loop through and test every known static page
        pages = {'/terms': 'Terms of Service', '/privacy': 'Privacy Policy'}
        for page in pages:
            response = self.app.get(page)
            assert "<h2>" + pages[page] + "</h2>" in response, pages[page] + " not found"
            assert self.minify(response), pages[page] + " couldn't minify"


class TestTasks(TestBase):

    def test_tasks(self):
        response = self.app.get('/task/sessions')
        assert "OK" in response


class TestAdmin(TestBase):

    def test_admin(self):
        response = self.app.get('/admin')
        assert '<h2>Admin</h2>' in response

        # test clearing memcache out
        response = self.app.post('/admin', {"memcache": "1"})
        assert response.status_int == 302

