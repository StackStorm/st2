from pecan import rest

from st2api.controllers import resource
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionController(resource.ResourceController):
    model = ActionExecutionHistoryAPI
    access = ActionExecutionHistory
    supported_filters = {
        'action': 'action__name',
        'parent': 'parent',
        'rule': 'rule__name',
        'runner': 'runner__name',
        'timestamp': 'execution__start_timestamp',
        'trigger': 'trigger__name',
        'trigger_type': 'trigger_type__name',
        'user': 'execution__context__user'
    }


class HistoryController(rest.RestController):
    executions = ActionExecutionController()
