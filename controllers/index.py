from base import BaseController, renderIfCached


class IndexController(BaseController):
    """ handles request for the main index page of the site """

    @renderIfCached
    def get(self):

        self.cacheAndRenderTemplate('index.html')

