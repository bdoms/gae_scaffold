from controllers.base import BaseController, cacheAndRender


class SitemapController(BaseController):
    """ handles generating a sitemap """

    @cacheAndRender()
    def get(self):
        # FYI: sitemaps can only have a max of 50,000 URLs or be 10 MB each
        base_url = self.request.protocol + "://" + self.request.host

        self.renderTemplate('sitemap.xml', base_url=base_url)
