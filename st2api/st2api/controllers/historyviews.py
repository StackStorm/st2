from pecan.rest import RestController
import six

from st2common import log as logging
from st2common.models.base import jsexpose
from st2common.persistence.history import ActionExecutionHistory

LOG = logging.getLogger(__name__)

SUPPORTED_FILTERS = {
    'action': 'action.name',
    'parent': 'parent',
    'rule': 'rule.name',
    'runner': 'runner.name',
    'timestamp': 'execution.start_timestamp',
    'trigger': 'trigger.name',
    'trigger_type': 'trigger_type.name',
    'user': 'execution.context.user'
}

IGNORE_FILTERS = ['parent', 'timestamp']  # Both are too broad. We should threat them differently.


class FiltersController(RestController):
    @jsexpose()
    def get_all(self):
        """
            List all distinct filters.

            Handles requests:
                GET /history/executions/views/filters
        """
        LOG.info('GET all /history/executions/views/filters')

        filters = {}

        for name, field in six.iteritems(SUPPORTED_FILTERS):
            if name not in IGNORE_FILTERS:
                filters[name] = ActionExecutionHistory.distinct(field=field)

        return filters


class HistoryViewsController(RestController):
    filters = FiltersController()
