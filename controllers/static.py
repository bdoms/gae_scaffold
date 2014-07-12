from base import BaseController, renderIfCached


class StaticController(BaseController):
    """ handles any page that doesn't need to render with custom variables """

    @renderIfCached
    def get(self, *args):

        path = self.request.path
        filename = "static/" + path + ".html"
        page_title = path.replace("/", " ").strip().title()

        self.cacheAndRenderTemplate(filename, page_title=page_title)
