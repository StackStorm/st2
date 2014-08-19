from pecan import expose

from st2datastore.controllers import datastore


class RootController(object):

    keys = datastore.KeyValuePairController()

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
