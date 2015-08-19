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

import copy
import re

import jsonschema
from oslo_config import cfg
import pecan
from pecan import abort
from six.moves import http_client

from st2api.controllers.base import BaseRestControllerMixin
from st2api.controllers.resource import ResourceController
from st2api.controllers.v1.executionviews import ExecutionViewsController
from st2api.controllers.v1.executionviews import SUPPORTED_FILTERS
from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_CANCELED
from st2common.constants.action import CANCELABLE_STATES
from st2common.exceptions.trace import UniqueTraceNotFoundException
from st2common.models.api.action import LiveActionAPI
from st2common.models.api.base import jsexpose
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.services import action as action_service
from st2common.services import executions as execution_service
from st2common.rbac.utils import request_user_is_admin
from st2common.util import jsonify
from st2common.util import isotime
from st2common.util import date as date_utils

__all__ = [
    'ActionExecutionsController'
]

LOG = logging.getLogger(__name__)

# Note: We initialize filters here and not in the constructor
SUPPORTED_EXECUTIONS_FILTERS = SUPPORTED_FILTERS
SUPPORTED_EXECUTIONS_FILTERS.update({
    'timestamp_gt': 'start_timestamp.gt',
    'timestamp_lt': 'start_timestamp.lt'
})

# Name of the query parameter for toggling on the display of secrets to the admin users in the API
# responses
SHOW_SECRETS_QUERY_PARAM = 'show_secrets'

MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsControllerMixin(BaseRestControllerMixin):
    """
    Mixin class with shared methods.
    """

    model = ActionExecutionAPI
    access = ActionExecution

    # A list of attributes which can be specified using ?exclude_attributes filter
    valid_exclude_attributes = [
        'result',
        'trigger_instance'
    ]

    def _get_from_model_kwargs_for_request(self, request):
        """
        Set mask_secrets=False if the user is an admin and provided ?show_secrets=True query param.
        """
        from_model_kwargs = {'mask_secrets': cfg.CONF.api.mask_secrets}

        show_secrets = self._get_query_param_value(request=request,
                                                   param_name=SHOW_SECRETS_QUERY_PARAM,
                                                   param_type='bool',
                                                   default_value=False)

        if show_secrets and request_user_is_admin(request=request):
            from_model_kwargs['mask_secrets'] = False

        return from_model_kwargs

    def _handle_schedule_execution(self, liveaction):
        try:
            return self._schedule_execution(liveaction=liveaction)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, str(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, re.sub("u'([^']*)'", r"'\1'", e.message))
        except UniqueTraceNotFoundException as e:
            abort(http_client.BAD_REQUEST, str(e))
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, str(e))

    def _schedule_execution(self, liveaction):
        # Initialize execution context if it does not exist.
        if not hasattr(liveaction, 'context'):
            liveaction.context = dict()

        # Retrieve username of the authed user (note - if auth is disabled, user will not be
        # set so we fall back to the system user name)
        request_token = pecan.request.context.get('token', None)

        if request_token:
            user = request_token.user
        else:
            user = cfg.CONF.system_user.user

        liveaction.context['user'] = user
        LOG.debug('User is: %s' % user)

        # Retrieve other st2 context from request header.
        if 'st2-context' in pecan.request.headers and pecan.request.headers['st2-context']:
            context = jsonify.try_loads(pecan.request.headers['st2-context'])
            if not isinstance(context, dict):
                raise ValueError('Unable to convert st2-context from the headers into JSON.')
            liveaction.context.update(context)

        # Schedule the action execution.
        liveactiondb = LiveActionAPI.to_model(liveaction)
        _, actionexecutiondb = action_service.request(liveactiondb)
        from_model_kwargs = self._get_from_model_kwargs_for_request(request=pecan.request)
        return ActionExecutionAPI.from_model(actionexecutiondb, from_model_kwargs)

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
        from_model_kwargs = self._get_from_model_kwargs_for_request(request=pecan.request)
        LOG.debug('retrieving children for id: %s with depth: %s', id_, depth)
        descendants = execution_service.get_descendants(actionexecution_id=id_,
                                                        descendant_depth=depth,
                                                        result_fmt=result_fmt)

        return [self.model.from_model(descendant, from_model_kwargs) for
                descendant in descendants]

    def _validate_exclude_fields(self, exclude_fields):
        """
        Validate that provided exclude fields are valid.
        """
        if not exclude_fields:
            return exclude_fields

        for field in exclude_fields:
            if field not in self.valid_exclude_attributes:
                msg = 'Invalid or unsupported attribute specified: %s' % (field)
                raise ValueError(msg)

        return exclude_fields


class ActionExecutionChildrenController(ActionExecutionsControllerMixin):
    @jsexpose(arg_types=[str])
    def get(self, id, **kwargs):
        """
        Retrieve children for the provided action execution.

        :rtype: ``list``
        """
        return self._get_children(id_=id, **kwargs)


class ActionExecutionAttributeController(ActionExecutionsControllerMixin):
    @jsexpose()
    def get(self, id, attribute, **kwargs):
        """
        Retrieve a particular attribute for the provided action execution.

        Handles requests:

            GET /actionexecutions/<id>/<attribute>

        :rtype: ``dict``
        """
        fields = [attribute]
        fields = self._validate_exclude_fields(fields)
        action_exec_db = self.access.impl.model.objects.filter(id=id).only(*fields).get()
        result = getattr(action_exec_db, attribute, None)
        return result


class ActionExecutionReRunController(ActionExecutionsControllerMixin, ResourceController):
    supported_filters = {}
    exclude_fields = [
        'result',
        'trigger_instance'
    ]

    class ExecutionParameters(object):
        def __init__(self, parameters=None):
            self.parameters = parameters or {}

        def validate(self):
            if self.parameters:
                assert isinstance(self.parameters, dict)

            return True

    @jsexpose(body_cls=ExecutionParameters, status_code=http_client.CREATED)
    def post(self, execution_parameters, execution_id):
        """
        Re-run the provided action execution optionally specifying override parameters.

        Handles requests:

            POST /executions/<id>/re_run
        """
        parameters = execution_parameters.parameters

        # Note: We only really need parameters here
        existing_execution = self._get_one(id=execution_id, exclude_fields=self.exclude_fields)

        # Merge in any parameters provided by the user
        new_parameters = copy.deepcopy(existing_execution.parameters)
        new_parameters.update(parameters)

        # Create object for the new execution
        action_ref = existing_execution.action['ref']
        new_liveaction = LiveActionDB(action=action_ref, parameters=new_parameters)

        result = self._handle_schedule_execution(liveaction=new_liveaction)
        return result


class ActionExecutionsController(ActionExecutionsControllerMixin, ResourceController):
    """
        Implements the RESTful web endpoint that handles
        the lifecycle of ActionExecutions in the system.
    """

    # Nested controllers
    views = ExecutionViewsController()

    children = ActionExecutionChildrenController()
    attribute = ActionExecutionAttributeController()
    re_run = ActionExecutionReRunController()

    # ResourceController attributes
    query_options = {
        'sort': ['-start_timestamp', 'action.ref']
    }
    supported_filters = SUPPORTED_EXECUTIONS_FILTERS
    filter_transform_functions = {
        'timestamp_gt': lambda value: isotime.parse(value=value),
        'timestamp_lt': lambda value: isotime.parse(value=value)
    }

    @jsexpose()
    def get_all(self, exclude_attributes=None, **kw):
        """
        List all actionexecutions.

        Handles requests:
            GET /actionexecutions[?exclude_attributes=result,trigger_instance]

        :param exclude_attributes: Comma delimited string of attributes to exclude from the object.
        :type exclude_attributes: ``str``
        """
        if exclude_attributes:
            exclude_fields = exclude_attributes.split(',')
        else:
            exclude_fields = None

        exclude_fields = self._validate_exclude_fields(exclude_fields=exclude_fields)

        return self._get_action_executions(exclude_fields=exclude_fields, **kw)

    @jsexpose(arg_types=[str])
    def get_one(self, id, exclude_attributes=None, **kwargs):
        """
        Retrieve a single execution.

        Handles requests:
            GET /actionexecutions/<id>[?exclude_attributes=result,trigger_instance]

        :param exclude_attributes: Comma delimited string of attributes to exclude from the object.
        :type exclude_attributes: ``str``
        """
        if exclude_attributes:
            exclude_fields = exclude_attributes.split(',')
        else:
            exclude_fields = None

        exclude_fields = self._validate_exclude_fields(exclude_fields=exclude_fields)

        return self._get_one(id=id, exclude_fields=exclude_fields)

    @jsexpose(body_cls=LiveActionAPI, status_code=http_client.CREATED)
    def post(self, liveaction):
        return self._handle_schedule_execution(liveaction=liveaction)

    @jsexpose(arg_types=[str])
    def delete(self, exec_id):
        """
        Stops a single execution.

        Handles requests:
            DELETE /actionexecutions/<id>

        """
        execution_api = self._get_one(id=exec_id)

        if not execution_api:
            abort(http_client.NOT_FOUND, 'Execution with id %s not found.' % exec_id)
            return

        liveaction_id = execution_api.liveaction['id']
        if not liveaction_id:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)

        try:
            liveaction_db = LiveAction.get_by_id(liveaction_id)
        except:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)
            return

        if liveaction_db.status == LIVEACTION_STATUS_CANCELED:
            abort(http_client.OK,
                  'Action is already in "canceled" state.')

        if liveaction_db.status not in CANCELABLE_STATES:
            abort(http_client.OK,
                  'Action cannot be canceled. State = %s.' % liveaction_db.status)
            return

        liveaction_db.status = 'canceled'
        liveaction_db.end_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db.result = {'message': 'Action canceled by user.'}
        try:
            LiveAction.add_or_update(liveaction_db)
        except:
            LOG.exception('Failed updating status to canceled for liveaction %s.',
                          liveaction_db.id)
            abort(http_client.INTERNAL_SERVER_ERROR, 'Failed canceling execution.')
            return

        execution_db = execution_service.update_execution(liveaction_db)
        from_model_kwargs = self._get_from_model_kwargs_for_request(request=pecan.request)
        return ActionExecutionAPI.from_model(execution_db, from_model_kwargs)

    @jsexpose()
    def options(self, *args, **kw):
        return

    def _get_action_executions(self, exclude_fields=None, **kw):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """
        kw['limit'] = int(kw.get('limit', 100))

        LOG.debug('Retrieving all action executions with filters=%s', kw)
        return super(ActionExecutionsController, self)._get_all(exclude_fields=exclude_fields,
                                                                **kw)
