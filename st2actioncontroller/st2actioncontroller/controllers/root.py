import httplib
from pecan import expose
from webob.exc import status_map

from st2common import log as logging
from st2actioncontroller.controllers.actions import ActionsController
from st2actioncontroller.controllers.actionexecutions import ActionExecutionsController
from st2actioncontroller.controllers.actiontypes import ActionTypesController

LOG = logging.getLogger('st2actioncontroller')


class RootController(object):
    # Handler for /actions/
    actions = ActionsController()
    # Handler for /actionexecutions/
    actionexecutions = ActionExecutionsController()
    # Handler for /actiontypes/
    actiontypes = ActionTypesController()

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
