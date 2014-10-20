from pecan import rest

from st2api.controllers import resource
from st2api.controllers.historyviews import SUPPORTED_FILTERS
from st2api.controllers.historyviews import HistoryViewsController
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common import log as logging

LOG = logging.getLogger(__name__)


class ActionExecutionController(resource.ResourceController):
    views = HistoryViewsController()

    model = ActionExecutionHistoryAPI
    access = ActionExecutionHistory

    supported_filters = SUPPORTED_FILTERS

    options = {
        'sort': ['-execution__start_timestamp']
    }


class HistoryController(rest.RestController):
    executions = ActionExecutionController()
