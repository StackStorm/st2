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

from pecan import rest

from st2api.controllers import resource
from st2api.controllers.v1.historyviews import SUPPORTED_FILTERS
from st2api.controllers.v1.historyviews import HistoryViewsController
from st2common.persistence.history import ActionExecutionHistory
from st2common.models.api.history import ActionExecutionHistoryAPI
from st2common.models.api.base import jsexpose
from st2common.models.system.common import ResourceReference
from st2common import log as logging

LOG = logging.getLogger(__name__)


class ActionExecutionHistoryController(resource.ResourceController):
    model = ActionExecutionHistoryAPI
    access = ActionExecutionHistory
    views = HistoryViewsController()

    supported_filters = SUPPORTED_FILTERS

    query_options = {
        'sort': ['-execution__start_timestamp']
    }

    def _get_executions(self, **kw):
        action_ref = kw.get('action', None)

        if action_ref:
            action_name = ResourceReference.get_name(action_ref)
            action_pack = ResourceReference.get_pack(action_ref)
            del kw['action']
            kw['action.name'] = action_name
            kw['action.pack'] = action_pack

        return super(ActionExecutionHistoryController, self)._get_all(**kw)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all history for action liveactions.

            Handles requests:
                GET /history/liveactions/
        """
        LOG.info('GET all /history/liveactions/ with filters=%s', kw)
        return self._get_executions(**kw)


class HistoryController(rest.RestController):
    liveactions = ActionExecutionHistoryController()
