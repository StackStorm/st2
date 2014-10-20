from pecan import rest

from st2api.controllers import resource
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common.models.base import jsexpose
from st2common.models.db.action import ActionReference
from st2common import log as logging


LOG = logging.getLogger(__name__)


class ActionExecutionHistoryController(resource.ResourceController):
    model = ActionExecutionHistoryAPI
    access = ActionExecutionHistory

    supported_filters = {
        'action': 'action__name',  # XXX: Hack to declare a filter that has no direct data mapping.
        'action_name': 'action__name',
        'action_pack': 'action__content_pack',
        'parent': 'parent',
        'rule': 'rule__name',
        'runner': 'runner__name',
        'timestamp': 'execution__start_timestamp',
        'trigger': 'trigger__name',
        'trigger_type': 'trigger_type__name',
        'user': 'execution__context__user'
    }

    query_options = {
        'sort': ['-execution__start_timestamp']
    }

    def _get_executions(self, **kw):
        action_ref = kw.get('action', None)

        if action_ref:
            action_name = ActionReference.get_name(action_ref)
            action_pack = ActionReference.get_pack(action_ref)
            del kw['action']
            kw['action_name'] = action_name
            kw['action_pack'] = action_pack

        return super(ActionExecutionHistoryController, self)._get_all(**kw)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all history for action executions.

            Handles requests:
                GET /history/executions/
        """
        LOG.info('GET all /history/executions/ with filters=%s', kw)
        return self._get_executions(**kw)


class HistoryController(rest.RestController):
    executions = ActionExecutionHistoryController()
