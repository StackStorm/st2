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

from pecan.rest import RestController
import six

from st2common import log as logging
from st2common.models.api.base import jsexpose
from st2common.persistence.execution import ActionExecution

LOG = logging.getLogger(__name__)

# List of supported filters and relation between filter name and execution property it represents.
# The same list is used both in ActionExecutionController to map filter names to properties and
# in FiltersController below to generate a list of unique values for each filter for UI so user
# could pick a filter from a drop down.
# If filter is unique for every execution or repeats very rarely (ex. execution id or parent
# reference) it should be also added to IGNORE_FILTERS to avoid bloating FiltersController
# response. Failure to do so will eventually result in Chrome hanging out while opening History
# tab of st2web.
SUPPORTED_FILTERS = {
    'action': 'action.ref',
    'status': 'status',
    'liveaction': 'liveaction.id',
    'parent': 'parent',
    'rule': 'rule.name',
    'runner': 'runner.name',
    'timestamp': 'start_timestamp',
    'trigger': 'trigger.name',
    'trigger_type': 'trigger_type.name',
    'trigger_instance': 'trigger_instance.id',
    'user': 'context.user'
}

# List of filters that are too broad to distinct by them and are very likely to represent 1 to 1
# relation between filter and particular history record.
IGNORE_FILTERS = ['parent', 'timestamp', 'liveaction', 'trigger_instance']


class FiltersController(RestController):
    @jsexpose()
    def get_all(self):
        """
            List all distinct filters.

            Handles requests:
                GET /executions/views/filters
        """
        filters = {}

        for name, field in six.iteritems(SUPPORTED_FILTERS):
            if name not in IGNORE_FILTERS:
                filters[name] = ActionExecution.distinct(field=field)

        return filters


class ExecutionViewsController(RestController):
    filters = FiltersController()
