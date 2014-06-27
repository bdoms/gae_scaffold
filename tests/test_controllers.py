from webtest import TestApp

from base import BaseTestCase


class TestBase(BaseTestCase):

    def setUp(self):
        super(TestBase, self).setUp()
        # this must be imported after the above setup in order for the stubs to work
        from website import app
        self.app = TestApp(app)


class TestError(TestBase):

    def test_error(self):
        # this just covers any URL not handled by something else - always produces 404
        assert self.app.get('/nothing-to-see-here', status=404)


class TestIndex(TestBase):

    def test_index(self):
        response = self.app.get('/')
        assert '<h2>Index Page</h2>' in response


class TestSitemap(TestBase):

    def test_sitemap(self):
        response = self.app.get('/sitemap.xml')
        assert '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' in response


class TestStatic(TestBase):

    def test_static(self):
        # loop through and test every known static page
        pages = {'/terms': 'Terms of Service', '/privacy': 'Privacy Policy'}
        for page in pages:
            response = self.app.get(page)
            assert "<h2>" + pages[page] + "</h2>" in response, pages[page] + " not found"


class TestAdmin(TestBase):

    def test_admin(self):
        response = self.app.get('/admin')
        assert '<h2>Admin</h2>' in response

        # test clearing memcache out
        response = self.app.post('/admin', {"memcache": "1"})
        assert response.status_int == 302
