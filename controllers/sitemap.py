from base import BaseController, renderIfCached


class SitemapController(BaseController):
    """ handles generating a sitemap """

    @renderIfCached
    def get(self):
        # FYI: sitemaps can only have a max of 50,000 URLs or be 10 MB each
        base_url = "http://" + self.request.headers.get("host")

        self.cacheAndRenderTemplate('sitemap.xml', base_url=base_url)

