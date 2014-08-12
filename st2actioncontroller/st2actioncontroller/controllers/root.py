import httplib
from pecan import expose
from webob.exc import status_map

from st2common import log as logging
from st2actioncontroller.controllers.actions import ActionsController
from st2actioncontroller.controllers.actionexecutions import ActionExecutionsController
from st2actioncontroller.controllers.runnertypes import RunnerTypesController

LOG = logging.getLogger('st2actioncontroller')


class RootController(object):
    # Handler for /actions/
    actions = ActionsController()
    # Handler for /actionexecutions/
    actionexecutions = ActionExecutionsController()
    # Handler for /runnertypes/
    runnertypes = RunnerTypesController()

# TODO: Remove index handler
    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
