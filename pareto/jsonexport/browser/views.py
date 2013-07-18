from Products.Five import BrowserView

from ..service import service


class JsonView(BrowserView):
    def __call__(self):
        self.request.RESPONSE.setHeader('Content-Type', 'application/json')
        return service.render(
            self.context, recursive=self.request.get('recursive'))
