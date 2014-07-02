from pecan import expose
from webob.exc import status_map

from st2datastore.controllers import datastore


class RootController(object):

    keys = datastore.KeyValuePairController()

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()

    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:  # pragma: no cover
            status = 500
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)
