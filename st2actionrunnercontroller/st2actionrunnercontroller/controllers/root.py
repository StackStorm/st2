import httplib
from pecan import expose, redirect
from webob.exc import status_map

from wsmeext.pecan import wsexpose

from st2common import log as logging
from st2actionrunnercontroller.controllers.liveactions import LiveActionsController


LOG = logging.getLogger(__name__)


class RootController(object):
    # actionrunners = ActionRunnersController()
    liveactions = LiveActionsController()

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
