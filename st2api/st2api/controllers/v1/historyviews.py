# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from itertools import chain
from pecan.rest import RestController
import six

from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.persistence.history import ActionExecution

LOG = logging.getLogger(__name__)

SUPPORTED_FILTERS = {
    'action': ('action.pack', 'action.name'),  # XXX: Compound filter. For aggregation only.
    'action.name': 'action.name',
    'action.pack': 'action.pack',
    'execution': 'execution.id',
    'parent': 'parent',
    'rule': 'rule.name',
    'runner': 'runner.name',
    'timestamp': 'execution.start_timestamp',
    'trigger': 'trigger.name',
    'trigger_type': 'trigger_type.name',
    'user': 'execution.context.user'
}

# List of filters that are too broad to distinct by them and are very likely to represent 1 to 1
# relation between filter and particular history record.
IGNORE_FILTERS = ['parent', 'timestamp', 'execution']


class FiltersController(RestController):
    @jsexpose()
    def get_all(self):
        """
            List all distinct filters.

            Handles requests:
                GET /history/liveactions/views/filters
        """
        LOG.info('GET all /history/liveactions/views/filters')

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

                aggregate = ActionExecution.aggregate([
                    {'$group': {'_id': query}}
                ])

                filters[name] = [res['_id'] for res in aggregate['result'] if res['_id']]

        return filters


class HistoryViewsController(RestController):
    filters = FiltersController()
