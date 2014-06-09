import httplib
import logging
from pecan import expose, redirect
from webob.exc import status_map

from wsmeext.pecan import wsexpose

from st2actioncontroller.controllers.actions import StactionsController
from st2actioncontroller.controllers.actionexecutions import StactionExecutionsController


LOG = logging.getLogger('st2actioncontroller')


class RootController(object):
    actions = StactionsController()
    actionexecutions = StactionExecutionsController()

# TODO: Remove index handler
    @expose(generic=True, template='index.html')
    def index(self):
        return dict()

#    @index.when(method='POST')
#    def index_post(self, q):
#        redirect('http://pecan.readthedocs.org/en/latest/search.html?q=%s' % q)
#
    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:  # pragma: no cover
            status = httplib.INTERNAL_SERVER_ERROR
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)
