import httplib
from pecan import expose, redirect
from webob.exc import status_map

from st2common import log as logging
from st2actionrunnercontroller.controllers.liveactions import LiveActionsController


LOG = logging.getLogger(__name__)


class RootController(object):
    liveactions = LiveActionsController()

    # TODO: Remove index handler
    @expose(generic=True, template='index.html')
    def index(self):
        return dict()
