from pecan import rest

from st2api.controllers import resource
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common import log as logging


LOG = logging.getLogger(__name__)

MANAGER = resource.ResourceManager(ActionExecutionHistoryAPI, ActionExecutionHistory)

SUPPORTED_FILTERS = {
    'action': 'action__name',
    'rule': 'rule__name',
    'runner': 'runner__name',
    'trigger': 'trigger__name',
    'trigger_type': 'trigger_type__name',
    'user': 'execution__context__user'
}


class ActionExecutionController(rest.RestController, resource.QueryMixin):
    pass


class HistoryController(rest.RestController):
    executions = ActionExecutionController(MANAGER, SUPPORTED_FILTERS)
