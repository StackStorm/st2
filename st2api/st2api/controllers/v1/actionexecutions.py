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

import jsonschema
from oslo.config import cfg
import pecan
from pecan import abort
from pecan.rest import RestController
from six.moves import http_client

from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.executionviews import ExecutionViewsController
from st2api.controllers.v1.executionviews import SUPPORTED_FILTERS
from st2common import log as logging
from st2common.models.api.action import LiveActionAPI
from st2common.models.api.base import jsexpose
from st2common.models.api.execution import ActionExecutionAPI
from st2common.persistence.execution import ActionExecution
from st2common.services import action as action_service
from st2common.services import executions as execution_service
from st2common.util import jsonify
from st2common.util import isotime

__all__ = [
    'ActionExecutionsController'
]

LOG = logging.getLogger(__name__)

MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsControllerMixin(RestController):
    """
    Mixin class with shared methods.
    """

    model = ActionExecutionAPI
    access = ActionExecution

    def _get_result_object(self, id):
        """
        Retrieve result object for the provided action execution.

        :param id: Action execution ID.
        :type id: ``str``

        :rtype: ``dict``
        """
        fields = ['result']
        action_exec_db = self.access.impl.model.objects.filter(id=id).only(*fields).get()
        return action_exec_db.result

    def _get_children(self, id_, depth=-1, result_fmt=None):
        # make sure depth is int. Url encoding will make it a string and needs to
        # be converted back in that case.
        depth = int(depth)
        LOG.debug('retrieving children for id: %s with depth: %s', id_, depth)
        descendants = execution_service.get_descendants(actionexecution_id=id_,
                                                        descendant_depth=depth,
                                                        result_fmt=result_fmt)
        return [self.model.from_model(descendant) for descendant in descendants]



class ActionExecutionChildrenController(ActionExecutionsControllerMixin):
    @jsexpose(str)
    def get(self, id, **kwargs):
        """
        Retrieve children for the provided action execution.

        :rtype: ``list``
        """
        return self._get_children(id_=id, **kwargs)


class ActionExecutionResultController(ActionExecutionsControllerMixin):
    @jsexpose(str)
    def get(self, id):
        """
        Retrieve result object for the provided action execution.

        Handles requests:

            GET /actionexecutions/<id>/result

        :rtype: ``dict``
        """
        result = self._get_result_object(id=id)
        return result


class ActionExecutionStdoutController(ActionExecutionsControllerMixin):
    @jsexpose(str)
    def get(self, id):
        """
        Retrieve raw stdout (if any) for the provided action execution.

        :rtype: ``str`` or ``None``
        """
        result = self._get_result_object(id=id)
        stdout = result.get('stdout', None)
        return stdout


class ActionExecutionStderrController(ActionExecutionsControllerMixin):
    @jsexpose(str)
    def get(self, id):
        """
        Retrieve raw stderr (if any) for the provided action execution.

        :rtype: ``str`` or ``None``
        """
        result = self._get_result_object(id=id)
        stderr = result.get('stderr', None)
        return stderr


class ActionExecutionsController(ActionExecutionsControllerMixin, ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    # Nested controllers
    views = ExecutionViewsController()

    children = ActionExecutionChildrenController()
    result = ActionExecutionResultController()
    stdout = ActionExecutionStdoutController()
    stderr = ActionExecutionStderrController()

    query_options = {
        'sort': ['-start_timestamp', 'action']
    }
    supported_filters = {
        'timestamp_gt': 'start_timestamp.gt',
        'timestamp_lt': 'start_timestamp.lt'
    }
    filter_transform_functions = {
        'timestamp_gt': lambda value: isotime.parse(value=value),
        'timestamp_lt': lambda value: isotime.parse(value=value)
    }

    def __init__(self):
        super(ActionExecutionsController, self).__init__()
        # Add common execution view supported filters
        self.supported_filters.update(SUPPORTED_FILTERS)

    @jsexpose(str)
    def get_one(self, id, *args, **kwargs):
        return self._get_one(id=id)

    @jsexpose()
    def get_all(self, exclude_result='0', **kw):
        """
            List all actionexecutions.

            Handles requests:
                GET /actionexecutions/
        """
        exclude_result = exclude_result == '1'

        if exclude_result:
            exclude_fields = ['result']
        else:
            exclude_fields = None

        LOG.info('GET all /actionexecutions/ with filters=%s', kw)
        return self._get_action_executions(exclude_fields=exclude_fields, **kw)

    @jsexpose(body=LiveActionAPI, status_code=http_client.CREATED)
    def post(self, execution):
        try:
            # Initialize execution context if it does not exist.
            if not hasattr(execution, 'context'):
                execution.context = dict()

            # Retrieve username of the authed user (note - if auth is disabled, user will not be
            # set so we fall back to the system user name)
            request_token = pecan.request.context.get('token', None)

            if request_token:
                user = request_token.user
            else:
                user = cfg.CONF.system_user.user

            execution.context['user'] = user

            # Retrieve other st2 context from request header.
            if ('st2-context' in pecan.request.headers and pecan.request.headers['st2-context']):
                context = jsonify.try_loads(pecan.request.headers['st2-context'])
                if not isinstance(context, dict):
                    raise ValueError('Unable to convert st2-context from the headers into JSON.')
                execution.context.update(context)

            # Schedule the action execution.
            liveactiondb = LiveActionAPI.to_model(execution)
            _, actionexecutiondb = action_service.schedule(liveactiondb)
            return ActionExecutionAPI.from_model(actionexecutiondb)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))

    @jsexpose()
    def options(self, *args, **kw):
        return

    def _get_action_executions(self, exclude_fields=None, **kw):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        kw['limit'] = int(kw.get('limit', 100))

        LOG.debug('Retrieving all action liveactions with filters=%s', kw)
        return super(ActionExecutionsController, self)._get_all(exclude_fields=exclude_fields,
                                                                **kw)
