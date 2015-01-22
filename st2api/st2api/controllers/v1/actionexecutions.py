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

import json

import jsonschema
from oslo.config import cfg
import pecan
from pecan import abort
from six.moves import http_client

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.models.api.action import LiveActionAPI
from st2common.models.api.base import jsexpose
from st2common.persistence.action import LiveAction
from st2common.services import action as action_service

LOG = logging.getLogger(__name__)


MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsController(ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """
    model = LiveActionAPI
    access = LiveAction

    supported_filters = {
        'action': 'action'
    }

    query_options = {
        'sort': ['-start_timestamp', 'action']
    }

    def _get_action_executions(self, **kw):
        kw['limit'] = int(kw.get('limit', 50))

        LOG.debug('Retrieving all action executions with filters=%s', kw)
        return super(ActionExecutionsController, self)._get_all(**kw)

    @jsexpose()
    def get_all(self, **kw):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """
        LOG.info('GET all /actionexecutions/ with filters=%s', kw)
        return self._get_action_executions(**kw)

    @jsexpose(body=LiveActionAPI, status_code=http_client.CREATED)
    def post(self, execution):
        try:
            # Initialize execution context if it does not exist.
            if not hasattr(execution, 'context'):
                execution.context = dict()

            # Retrieve user context from the request header.
            user = pecan.request.headers.get('X-User-Name')
            if not user:
                user = cfg.CONF.system_user.user
            execution.context['user'] = user

            # Retrieve other st2 context from request header.
            if ('st2-context' in pecan.request.headers and pecan.request.headers['st2-context']):
                context = pecan.request.headers['st2-context'].replace("'", "\"")
                execution.context.update(json.loads(context))

            # Schedule the action execution.
            executiondb = LiveActionAPI.to_model(execution)
            executiondb = action_service.schedule(executiondb)
            return LiveActionAPI.from_model(executiondb)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))

    @jsexpose(str, body=LiveActionAPI)
    def put(self, id, liveaction):
        try:
            liveaction_db = LiveAction.get_by_id(id)
        except:
            msg = 'liveaction by id: %s not found.' % id
            pecan.abort(http_client, msg)
        new_liveaction_db = LiveActionAPI.to_model(liveaction)
        if liveaction_db.status != new_liveaction_db.status:
            liveaction_db.status = new_liveaction_db.status
        if liveaction_db.result != new_liveaction_db.result:
            liveaction_db.result = new_liveaction_db.result
        if not liveaction_db.end_timestamp and new_liveaction_db.end_timestamp:
            liveaction_db.end_timestamp = new_liveaction_db.end_timestamp

        liveaction_db = LiveAction.add_or_update(liveaction_db)
        liveaction_api = LiveActionAPI.from_model(liveaction_db)
        return liveaction_api

    @jsexpose()
    def options(self):
        return
