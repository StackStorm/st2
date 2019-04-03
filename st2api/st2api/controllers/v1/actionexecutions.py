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
import sys
import traceback

import six
import jsonschema
from oslo_config import cfg
from six.moves import http_client

from st2api.controllers.base import BaseRestControllerMixin
from st2api.controllers.resource import ResourceController
from st2api.controllers.resource import BaseResourceIsolationControllerMixin
from st2api.controllers.v1.execution_views import ExecutionViewsController
from st2api.controllers.v1.execution_views import SUPPORTED_FILTERS
from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions import actionrunner as runner_exc
from st2common.exceptions import apivalidation as validation_exc
from st2common.exceptions import param as param_exc
from st2common.exceptions import trace as trace_exc
from st2common.models.api.action import LiveActionAPI
from st2common.models.api.action import LiveActionCreateAPI
from st2common.models.api.base import cast_argument_value
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.auth import UserDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.persistence.execution import ActionExecutionOutput
from st2common.router import abort
from st2common.router import Response
from st2common.services import action as action_service
from st2common.services import executions as execution_service
from st2common.services import trace as trace_service
from st2common.services import rbac as rbac_service
from st2common.util import isotime
from st2common.util import action_db as action_utils
from st2common.util import param as param_utils
from st2common.util.jsonify import try_loads
from st2common.rbac.types import PermissionType
from st2common.rbac.backends import get_rbac_backend

__all__ = [
    'ActionExecutionsController'
]

LOG = logging.getLogger(__name__)

# Note: We initialize filters here and not in the constructor
SUPPORTED_EXECUTIONS_FILTERS = copy.deepcopy(SUPPORTED_FILTERS)
SUPPORTED_EXECUTIONS_FILTERS.update({
    'timestamp_gt': 'start_timestamp.gt',
    'timestamp_lt': 'start_timestamp.lt'
})

MONITOR_THREAD_EMPTY_Q_SLEEP_TIME = 5
MONITOR_THREAD_NO_WORKERS_SLEEP_TIME = 1


class ActionExecutionsControllerMixin(BaseRestControllerMixin):
    """
    Mixin class with shared methods.
    """

    model = ActionExecutionAPI
    access = ActionExecution

    # Those two attributes are mandatory so we can correctly determine and mask secret execution
    # parameters
    mandatory_include_fields_retrieve = [
        'action.parameters',
        'runner.runner_parameters',
        'parameters'
    ]

    # A list of attributes which can be specified using ?exclude_attributes filter
    # NOTE: Allowing user to exclude attribute such as action and runner would break secrets
    # masking
    valid_exclude_attributes = [
        'result',
        'trigger_instance',
        'status'
    ]

    def _handle_schedule_execution(self, liveaction_api, requester_user, context_string=None,
                                   show_secrets=False):
        """
        :param liveaction: LiveActionAPI object.
        :type liveaction: :class:`LiveActionAPI`
        """
        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        # Assert action ref is valid
        action_ref = liveaction_api.action
        action_db = action_utils.get_action_by_ref(action_ref)

        if not action_db:
            message = 'Action "%s" cannot be found.' % (action_ref)
            LOG.warning(message)
            abort(http_client.BAD_REQUEST, message)

        # Assert the permissions
        permission_type = PermissionType.ACTION_EXECUTE
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_db,
                                                          permission_type=permission_type)

        # Validate that the authenticated user is admin if user query param is provided
        user = liveaction_api.user or requester_user.name
        rbac_utils.assert_user_is_admin_if_user_query_param_is_provided(user_db=requester_user,
                                                                        user=user)

        try:
            return self._schedule_execution(liveaction=liveaction_api,
                                            requester_user=requester_user,
                                            user=user,
                                            context_string=context_string,
                                            show_secrets=show_secrets,
                                            action_db=action_db)
        except ValueError as e:
            LOG.exception('Unable to execute action.')
            abort(http_client.BAD_REQUEST, six.text_type(e))
        except jsonschema.ValidationError as e:
            LOG.exception('Unable to execute action. Parameter validation failed.')
            abort(http_client.BAD_REQUEST, re.sub("u'([^']*)'", r"'\1'",
                                                  getattr(e, 'message', six.text_type(e))))
        except trace_exc.TraceNotFoundException as e:
            abort(http_client.BAD_REQUEST, six.text_type(e))
        except validation_exc.ValueValidationException as e:
            raise e
        except Exception as e:
            LOG.exception('Unable to execute action. Unexpected error encountered.')
            abort(http_client.INTERNAL_SERVER_ERROR, six.text_type(e))

    def _schedule_execution(self, liveaction, requester_user, action_db, user=None,
                            context_string=None, show_secrets=False):
        # Initialize execution context if it does not exist.
        if not hasattr(liveaction, 'context'):
            liveaction.context = dict()

        liveaction.context['user'] = user
        liveaction.context['pack'] = action_db.pack

        LOG.debug('User is: %s' % liveaction.context['user'])

        # Retrieve other st2 context from request header.
        if context_string:
            context = try_loads(context_string)
            if not isinstance(context, dict):
                raise ValueError('Unable to convert st2-context from the headers into JSON.')
            liveaction.context.update(context)

        # Include RBAC context (if RBAC is available and enabled)
        if cfg.CONF.rbac.enable:
            user_db = UserDB(name=user)
            role_dbs = rbac_service.get_roles_for_user(user_db=user_db, include_remote=True)
            roles = [role_db.name for role_db in role_dbs]
            liveaction.context['rbac'] = {
                'user': user,
                'roles': roles
            }

        # Schedule the action execution.
        liveaction_db = LiveActionAPI.to_model(liveaction)
        runnertype_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])

        try:
            liveaction_db.parameters = param_utils.render_live_params(
                runnertype_db.runner_parameters, action_db.parameters, liveaction_db.parameters,
                liveaction_db.context)
        except param_exc.ParamException:
            # We still need to create a request, so liveaction_db is assigned an ID
            liveaction_db, actionexecution_db = action_service.create_request(
                liveaction=liveaction_db,
                action_db=action_db,
                runnertype_db=runnertype_db)

            # By this point the execution is already in the DB therefore need to mark it failed.
            _, e, tb = sys.exc_info()
            action_service.update_status(
                liveaction=liveaction_db,
                new_status=action_constants.LIVEACTION_STATUS_FAILED,
                result={'error': six.text_type(e),
                        'traceback': ''.join(traceback.format_tb(tb, 20))})
            # Might be a good idea to return the actual ActionExecution rather than bubble up
            # the exception.
            raise validation_exc.ValueValidationException(six.text_type(e))

        # The request should be created after the above call to render_live_params
        # so any templates in live parameters have a chance to render.
        liveaction_db, actionexecution_db = action_service.create_request(liveaction=liveaction_db,
            action_db=action_db,
            runnertype_db=runnertype_db)

        _, actionexecution_db = action_service.publish_request(liveaction_db, actionexecution_db)
        mask_secrets = self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        execution_api = ActionExecutionAPI.from_model(actionexecution_db, mask_secrets=mask_secrets)

        return Response(json=execution_api, status=http_client.CREATED)

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

    def _get_children(self, id_, requester_user, depth=-1, result_fmt=None, show_secrets=False):
        # make sure depth is int. Url encoding will make it a string and needs to
        # be converted back in that case.
        depth = int(depth)
        LOG.debug('retrieving children for id: %s with depth: %s', id_, depth)
        descendants = execution_service.get_descendants(actionexecution_id=id_,
                                                        descendant_depth=depth,
                                                        result_fmt=result_fmt)

        mask_secrets = self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        return [self.model.from_model(descendant, mask_secrets=mask_secrets) for
                descendant in descendants]


class BaseActionExecutionNestedController(ActionExecutionsControllerMixin, ResourceController):
    # Note: We need to override "get_one" and "get_all" to return 404 since nested controller
    # don't implement thos methods

    # ResourceController attributes
    query_options = {}
    supported_filters = {}

    def get_all(self):
        abort(http_client.NOT_FOUND)

    def get_one(self, id):
        abort(http_client.NOT_FOUND)


class ActionExecutionChildrenController(BaseActionExecutionNestedController):
    def get_one(self, id, requester_user, depth=-1, result_fmt=None, show_secrets=False):
        """
        Retrieve children for the provided action execution.

        :rtype: ``list``
        """

        execution_db = self._get_one_by_id(id=id, requester_user=requester_user,
                                           permission_type=PermissionType.EXECUTION_VIEW)
        id = str(execution_db.id)

        return self._get_children(id_=id, depth=depth, result_fmt=result_fmt,
                                  requester_user=requester_user, show_secrets=show_secrets)


class ActionExecutionAttributeController(BaseActionExecutionNestedController):
    valid_exclude_attributes = ['action__pack', 'action__uid'] + \
        ActionExecutionsControllerMixin.valid_exclude_attributes

    def get(self, id, attribute, requester_user):
        """
        Retrieve a particular attribute for the provided action execution.

        Handles requests:

            GET /executions/<id>/attribute/<attribute name>

        :rtype: ``dict``
        """
        fields = [attribute, 'action__pack', 'action__uid']

        try:
            fields = self._validate_exclude_fields(fields)
        except ValueError:
            valid_attributes = ', '.join(ActionExecutionsControllerMixin.valid_exclude_attributes)
            msg = ('Invalid attribute "%s" specified. Valid attributes are: %s' %
                   (attribute, valid_attributes))
            raise ValueError(msg)

        action_exec_db = self.access.impl.model.objects.filter(id=id).only(*fields).get()

        permission_type = PermissionType.EXECUTION_VIEW
        rbac_utils = get_rbac_backend().get_utils_class()
        rbac_utils.assert_user_has_resource_db_permission(user_db=requester_user,
                                                          resource_db=action_exec_db,
                                                          permission_type=permission_type)

        result = getattr(action_exec_db, attribute, None)
        return Response(json=result, status=http_client.OK)


class ActionExecutionOutputController(ActionExecutionsControllerMixin, ResourceController):
    supported_filters = {
        'output_type': 'output_type'
    }
    exclude_fields = []

    def get_one(self, id, output_type='all', output_format='raw', existing_only=False,
                requester_user=None):
        # Special case for id == "last"
        if id == 'last':
            execution_db = ActionExecution.query().order_by('-id').limit(1).first()

            if not execution_db:
                raise ValueError('No executions found in the database')

            id = str(execution_db.id)

        execution_db = self._get_one_by_id(id=id, requester_user=requester_user,
                                           permission_type=PermissionType.EXECUTION_VIEW)
        execution_id = str(execution_db.id)

        query_filters = {}
        if output_type and output_type != 'all':
            query_filters['output_type'] = output_type

        def existing_output_iter():
            # Consume and return all of the existing lines
            # pylint: disable=no-member
            output_dbs = ActionExecutionOutput.query(execution_id=execution_id, **query_filters)

            output = ''.join([output_db.data for output_db in output_dbs])
            yield six.binary_type(output.encode('utf-8'))

        def make_response():
            app_iter = existing_output_iter()
            res = Response(content_type='text/plain', app_iter=app_iter)
            return res

        res = make_response()
        return res


class ActionExecutionReRunController(ActionExecutionsControllerMixin, ResourceController):
    supported_filters = {}
    exclude_fields = [
        'result',
        'trigger_instance'
    ]

    class ExecutionSpecificationAPI(object):
        def __init__(self, parameters=None, tasks=None, reset=None, user=None):
            self.parameters = parameters or {}
            self.tasks = tasks or []
            self.reset = reset or []
            self.user = user

        def validate(self):
            if (self.tasks or self.reset) and self.parameters:
                raise ValueError('Parameters override is not supported when '
                                 're-running task(s) for a workflow.')

            if self.parameters:
                assert isinstance(self.parameters, dict)

            if self.tasks:
                assert isinstance(self.tasks, list)

            if self.reset:
                assert isinstance(self.reset, list)

            if list(set(self.reset) - set(self.tasks)):
                raise ValueError('List of tasks to reset does not match the tasks to rerun.')

            return self

    def post(self, spec_api, id, requester_user, no_merge=False, show_secrets=False):
        """
        Re-run the provided action execution optionally specifying override parameters.

        Handles requests:

            POST /executions/<id>/re_run
        """

        if (spec_api.tasks or spec_api.reset) and spec_api.parameters:
            raise ValueError('Parameters override is not supported when '
                             're-running task(s) for a workflow.')

        if spec_api.parameters:
            assert isinstance(spec_api.parameters, dict)

        if spec_api.tasks:
            assert isinstance(spec_api.tasks, list)

        if spec_api.reset:
            assert isinstance(spec_api.reset, list)

        if list(set(spec_api.reset) - set(spec_api.tasks)):
            raise ValueError('List of tasks to reset does not match the tasks to rerun.')

        delay = None

        if hasattr(spec_api, "delay") and isinstance(spec_api.delay, int):
            delay = spec_api.delay

        no_merge = cast_argument_value(value_type=bool, value=no_merge)
        existing_execution = self._get_one_by_id(id=id, exclude_fields=self.exclude_fields,
                                                 requester_user=requester_user,
                                                 permission_type=PermissionType.EXECUTION_VIEW)

        if spec_api.tasks and existing_execution.runner['name'] != 'mistral-v2':
            raise ValueError('Task option is only supported for Mistral workflows.')

        # Merge in any parameters provided by the user
        new_parameters = {}
        if not no_merge:
            new_parameters.update(getattr(existing_execution, 'parameters', {}))
        new_parameters.update(spec_api.parameters)

        # Create object for the new execution
        action_ref = existing_execution.action['ref']

        # Include additional option(s) for the execution
        context = {
            're-run': {
                'ref': id,
            }
        }

        if spec_api.tasks:
            context['re-run']['tasks'] = spec_api.tasks

        if spec_api.reset:
            context['re-run']['reset'] = spec_api.reset

        # Add trace to the new execution
        trace = trace_service.get_trace_db_by_action_execution(
            action_execution_id=existing_execution.id)

        if trace:
            context['trace_context'] = {'id_': str(trace.id)}

        new_liveaction_api = LiveActionCreateAPI(action=action_ref,
                                                 context=context,
                                                 parameters=new_parameters,
                                                 user=spec_api.user,
                                                 delay=delay)

        return self._handle_schedule_execution(liveaction_api=new_liveaction_api,
                                               requester_user=requester_user,
                                               show_secrets=show_secrets)


class ActionExecutionsController(BaseResourceIsolationControllerMixin,
                                 ActionExecutionsControllerMixin, ResourceController):
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

    def get_all(self, requester_user, exclude_attributes=None, sort=None, offset=0, limit=None,
                show_secrets=False, include_attributes=None, advanced_filters=None, **raw_filters):
        """
        List all executions.

        Handles requests:
            GET /executions[?exclude_attributes=result,trigger_instance]

        :param exclude_attributes: List of attributes to exclude from the object.
        :type exclude_attributes: ``list``
        """
        # Use a custom sort order when filtering on a timestamp so we return a correct result as
        # expected by the user
        query_options = None
        if raw_filters.get('timestamp_lt', None) or raw_filters.get('sort_desc', None):
            query_options = {'sort': ['-start_timestamp', 'action.ref']}
        elif raw_filters.get('timestamp_gt', None) or raw_filters.get('sort_asc', None):
            query_options = {'sort': ['+start_timestamp', 'action.ref']}

        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }
        return self._get_action_executions(exclude_fields=exclude_attributes,
                                           include_fields=include_attributes,
                                           from_model_kwargs=from_model_kwargs,
                                           sort=sort,
                                           offset=offset,
                                           limit=limit,
                                           query_options=query_options,
                                           raw_filters=raw_filters,
                                           advanced_filters=advanced_filters,
                                           requester_user=requester_user)

    def get_one(self, id, requester_user, exclude_attributes=None, include_attributes=None,
                show_secrets=False):
        """
        Retrieve a single execution.

        Handles requests:
            GET /executions/<id>[?exclude_attributes=result,trigger_instance]

        :param exclude_attributes: List of attributes to exclude from the object.
        :type exclude_attributes: ``list``
        """
        exclude_fields = self._validate_exclude_fields(exclude_fields=exclude_attributes)
        include_fields = self._validate_include_fields(include_fields=include_attributes)

        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }

        # Special case for id == "last"
        if id == 'last':
            execution_db = ActionExecution.query().order_by('-id').limit(1).only('id').first()

            if not execution_db:
                raise ValueError('No executions found in the database')

            id = str(execution_db.id)

        return self._get_one_by_id(id=id, exclude_fields=exclude_fields,
                                   include_fields=include_fields,
                                   requester_user=requester_user,
                                   from_model_kwargs=from_model_kwargs,
                                   permission_type=PermissionType.EXECUTION_VIEW)

    def post(self, liveaction_api, requester_user, context_string=None, show_secrets=False):
        return self._handle_schedule_execution(liveaction_api=liveaction_api,
                                               requester_user=requester_user,
                                               context_string=context_string,
                                               show_secrets=show_secrets)

    def put(self, id, liveaction_api, requester_user, show_secrets=False):
        """
        Updates a single execution.

        Handles requests:
            PUT /executions/<id>

        """
        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }

        execution_api = self._get_one_by_id(id=id, requester_user=requester_user,
                                            from_model_kwargs=from_model_kwargs,
                                            permission_type=PermissionType.EXECUTION_STOP)

        if not execution_api:
            abort(http_client.NOT_FOUND, 'Execution with id %s not found.' % id)

        liveaction_id = execution_api.liveaction['id']
        if not liveaction_id:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)

        try:
            liveaction_db = LiveAction.get_by_id(liveaction_id)
        except:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)

        if liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES:
            abort(http_client.BAD_REQUEST, 'Execution is already in completed state.')

        def update_status(liveaction_api, liveaction_db):
            status = liveaction_api.status
            result = getattr(liveaction_api, 'result', None)
            liveaction_db = action_service.update_status(liveaction_db, status, result)
            actionexecution_db = ActionExecution.get(liveaction__id=str(liveaction_db.id))
            return (liveaction_db, actionexecution_db)

        try:
            if (liveaction_db.status == action_constants.LIVEACTION_STATUS_CANCELING and
                    liveaction_api.status == action_constants.LIVEACTION_STATUS_CANCELED):
                if action_service.is_children_active(liveaction_id):
                    liveaction_api.status = action_constants.LIVEACTION_STATUS_CANCELING
                liveaction_db, actionexecution_db = update_status(liveaction_api, liveaction_db)
            elif (liveaction_api.status == action_constants.LIVEACTION_STATUS_CANCELING or
                    liveaction_api.status == action_constants.LIVEACTION_STATUS_CANCELED):
                liveaction_db, actionexecution_db = action_service.request_cancellation(
                    liveaction_db, requester_user.name or cfg.CONF.system_user.user)
            elif (liveaction_db.status == action_constants.LIVEACTION_STATUS_PAUSING and
                    liveaction_api.status == action_constants.LIVEACTION_STATUS_PAUSED):
                if action_service.is_children_active(liveaction_id):
                    liveaction_api.status = action_constants.LIVEACTION_STATUS_PAUSING
                liveaction_db, actionexecution_db = update_status(liveaction_api, liveaction_db)
            elif (liveaction_api.status == action_constants.LIVEACTION_STATUS_PAUSING or
                    liveaction_api.status == action_constants.LIVEACTION_STATUS_PAUSED):
                liveaction_db, actionexecution_db = action_service.request_pause(
                    liveaction_db, requester_user.name or cfg.CONF.system_user.user)
            elif liveaction_api.status == action_constants.LIVEACTION_STATUS_RESUMING:
                liveaction_db, actionexecution_db = action_service.request_resume(
                    liveaction_db, requester_user.name or cfg.CONF.system_user.user)
            else:
                liveaction_db, actionexecution_db = update_status(liveaction_api, liveaction_db)
        except runner_exc.InvalidActionRunnerOperationError as e:
            LOG.exception('Failed updating liveaction %s. %s', liveaction_db.id, six.text_type(e))
            abort(http_client.BAD_REQUEST, 'Failed updating execution. %s' % six.text_type(e))
        except runner_exc.UnexpectedActionExecutionStatusError as e:
            LOG.exception('Failed updating liveaction %s. %s', liveaction_db.id, six.text_type(e))
            abort(http_client.BAD_REQUEST, 'Failed updating execution. %s' % six.text_type(e))
        except Exception as e:
            LOG.exception('Failed updating liveaction %s. %s', liveaction_db.id, six.text_type(e))
            abort(
                http_client.INTERNAL_SERVER_ERROR,
                'Failed updating execution due to unexpected error.'
            )

        mask_secrets = self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        execution_api = ActionExecutionAPI.from_model(actionexecution_db, mask_secrets=mask_secrets)

        return execution_api

    def delete(self, id, requester_user, show_secrets=False):
        """
        Stops a single execution.

        Handles requests:
            DELETE /executions/<id>

        """
        if not requester_user:
            requester_user = UserDB(cfg.CONF.system_user.user)

        from_model_kwargs = {
            'mask_secrets': self._get_mask_secrets(requester_user, show_secrets=show_secrets)
        }
        execution_api = self._get_one_by_id(id=id, requester_user=requester_user,
                                            from_model_kwargs=from_model_kwargs,
                                            permission_type=PermissionType.EXECUTION_STOP)

        if not execution_api:
            abort(http_client.NOT_FOUND, 'Execution with id %s not found.' % id)

        liveaction_id = execution_api.liveaction['id']
        if not liveaction_id:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)

        try:
            liveaction_db = LiveAction.get_by_id(liveaction_id)
        except:
            abort(http_client.INTERNAL_SERVER_ERROR,
                  'Execution object missing link to liveaction %s.' % liveaction_id)

        if liveaction_db.status == action_constants.LIVEACTION_STATUS_CANCELED:
            LOG.info(
                'Action %s already in "canceled" state; \
                returning execution object.' % liveaction_db.id
            )
            return execution_api

        if liveaction_db.status not in action_constants.LIVEACTION_CANCELABLE_STATES:
            abort(http_client.OK, 'Action cannot be canceled. State = %s.' % liveaction_db.status)

        try:
            (liveaction_db, execution_db) = action_service.request_cancellation(
                liveaction_db, requester_user.name or cfg.CONF.system_user.user)
        except:
            LOG.exception('Failed requesting cancellation for liveaction %s.', liveaction_db.id)
            abort(http_client.INTERNAL_SERVER_ERROR, 'Failed canceling execution.')

        return ActionExecutionAPI.from_model(execution_db,
                                             mask_secrets=from_model_kwargs['mask_secrets'])

    def _get_action_executions(self, exclude_fields=None, include_fields=None,
                               sort=None, offset=0, limit=None, advanced_filters=None,
                               query_options=None, raw_filters=None, from_model_kwargs=None,
                               requester_user=None):
        """
        :param exclude_fields: A list of object fields to exclude.
        :type exclude_fields: ``list``
        """

        if limit is None:
            limit = self.default_limit

        limit = int(limit)

        LOG.debug('Retrieving all action executions with filters=%s,exclude_fields=%s,'
                  'include_fields=%s', raw_filters, exclude_fields, include_fields)
        return super(ActionExecutionsController, self)._get_all(exclude_fields=exclude_fields,
                                                                include_fields=include_fields,
                                                                from_model_kwargs=from_model_kwargs,
                                                                sort=sort,
                                                                offset=offset,
                                                                limit=limit,
                                                                query_options=query_options,
                                                                raw_filters=raw_filters,
                                                                advanced_filters=advanced_filters,
                                                                requester_user=requester_user)


action_executions_controller = ActionExecutionsController()
action_execution_output_controller = ActionExecutionOutputController()
action_execution_rerun_controller = ActionExecutionReRunController()
action_execution_attribute_controller = ActionExecutionAttributeController()
action_execution_children_controller = ActionExecutionChildrenController()
