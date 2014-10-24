from itertools import chain
from pecan.rest import RestController
import six

from st2common import log as logging
from st2common.models.base import jsexpose
from st2common.persistence.history import ActionExecutionHistory

LOG = logging.getLogger(__name__)

SUPPORTED_FILTERS = {
    'action': ('action.pack', 'action.name'),  # XXX: Compound filter. For aggregation only.
    'action.name': 'action.name',
    'action.pack': 'action.pack',
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
                if isinstance(field, six.string_types):
                    query = '$' + field
                else:
                    dot_notation = list(chain.from_iterable(
                        ('$' + item, '.') for item in field
                    ))
                    dot_notation.pop(-1)
                    query = {'$concat': dot_notation}

                aggregate = ActionExecutionHistory.aggregate([
                    {'$group': {'_id': query}}
                ])

                filters[name] = [res['_id'] for res in aggregate['result'] if res['_id']]

        return filters


class HistoryViewsController(RestController):
    filters = FiltersController()
