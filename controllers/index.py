from controllers.base import BaseController, cacheAndRender


class IndexController(BaseController):
    """ handles request for the main index page of the site """

    @cacheAndRender()
    def get(self):

        self.renderTemplate('index.html')
