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

import six

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.trace import TraceNotFoundException
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.services import executions
from st2common.services import trace as trace_service
from st2common.util import date as date_utils
from st2common.util import action_db as action_utils
from st2common.util import schema as util_schema


__all__ = [
    'request',
    'create_request',
    'publish_request',
    'is_action_canceled_or_canceling'
]

LOG = logging.getLogger(__name__)


def _get_immutable_params(parameters):
    if not parameters:
        return []
    return [k for k, v in six.iteritems(parameters) if v.get('immutable', False)]


def create_request(liveaction):
    """
    Create an action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Use the user context from the parent action execution. Subtasks in a workflow
    # action can be invoked by a system user and so we want to use the user context
    # from the original workflow action.
    parent_context = executions.get_parent_context(liveaction)
    if parent_context:
        parent_user = parent_context.get('user', None)
        if parent_user:
            liveaction.context['user'] = parent_user

    # Validate action.
    action_db = action_utils.get_action_by_ref(liveaction.action)
    if not action_db:
        raise ValueError('Action "%s" cannot be found.' % liveaction.action)
    if not action_db.enabled:
        raise ValueError('Unable to execute. Action "%s" is disabled.' % liveaction.action)

    runnertype_db = action_utils.get_runnertype_by_name(action_db.runner_type['name'])

    if not hasattr(liveaction, 'parameters'):
        liveaction.parameters = dict()

    # Validate action parameters.
    schema = util_schema.get_schema_for_action_parameters(action_db)
    validator = util_schema.get_validator()
    util_schema.validate(liveaction.parameters, schema, validator, use_default=True,
                         allow_default_none=True)

    # validate that no immutable params are being overriden. Although possible to
    # ignore the override it is safer to inform the user to avoid surprises.
    immutables = _get_immutable_params(action_db.parameters)
    immutables.extend(_get_immutable_params(runnertype_db.runner_parameters))
    overridden_immutables = [p for p in six.iterkeys(liveaction.parameters) if p in immutables]
    if len(overridden_immutables) > 0:
        raise ValueError('Override of immutable parameter(s) %s is unsupported.'
                         % str(overridden_immutables))

    # Set notification settings for action.
    # XXX: There are cases when we don't want notifications to be sent for a particular
    # execution. So we should look at liveaction.parameters['notify']
    # and not set liveaction.notify.
    if not _is_notify_empty(action_db.notify):
        liveaction.notify = action_db.notify

    # Write to database and send to message queue.
    liveaction.status = action_constants.LIVEACTION_STATUS_REQUESTED
    liveaction.start_timestamp = date_utils.get_datetime_utc_now()

    # Set the "action_is_workflow" attribute
    liveaction.action_is_workflow = action_db.is_workflow()

    # Publish creation after both liveaction and actionexecution are created.
    liveaction = LiveAction.add_or_update(liveaction, publish=False)

    # Get trace_db if it exists. This could throw. If it throws, we have to cleanup
    # liveaction object so we don't see things in requested mode.
    trace_db = None
    try:
        _, trace_db = trace_service.get_trace_db_by_live_action(liveaction)
    except StackStormDBObjectNotFoundError as e:
        _cleanup_liveaction(liveaction)
        raise TraceNotFoundException(str(e))

    execution = executions.create_execution_object(liveaction, publish=False)

    if trace_db:
        trace_service.add_or_update_given_trace_db(
            trace_db=trace_db,
            action_executions=[
                trace_service.get_trace_component_for_action_execution(execution, liveaction)
            ])

    return liveaction, execution


def publish_request(liveaction, execution):
    """
    Publish an action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Assume that this is a creation.
    LiveAction.publish_create(liveaction)
    LiveAction.publish_status(liveaction)
    ActionExecution.publish_create(execution)

    extra = {'liveaction_db': liveaction, 'execution_db': execution}
    LOG.audit('Action execution requested. LiveAction.id=%s, ActionExecution.id=%s' %
              (liveaction.id, execution.id), extra=extra)

    return liveaction, execution


def request(liveaction):
    liveaction, execution = create_request(liveaction)
    liveaction, execution = publish_request(liveaction, execution)

    return liveaction, execution


def update_status(liveaction, new_status, result=None, publish=True):
    if liveaction.status == new_status:
        return liveaction

    old_status = liveaction.status

    liveaction = action_utils.update_liveaction_status(
        status=new_status, result=result, liveaction_id=liveaction.id, publish=False)

    action_execution = executions.update_execution(liveaction)

    msg = ('The status of action execution is changed from %s to %s. '
           '<LiveAction.id=%s, ActionExecution.id=%s>' % (old_status,
           new_status, liveaction.id, action_execution.id))

    extra = {
        'action_execution_db': action_execution,
        'liveaction_db': liveaction
    }

    LOG.audit(msg, extra=extra)
    LOG.info(msg)

    if publish:
        LiveAction.publish_status(liveaction)

    return liveaction


def is_action_canceled_or_canceling(liveaction_id):
    liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)
    return liveaction_db.status in [action_constants.LIVEACTION_STATUS_CANCELED,
                                    action_constants.LIVEACTION_STATUS_CANCELING]


def request_cancellation(liveaction, requester):
    """
    Request cancellation of an action execution.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    if liveaction.status == action_constants.LIVEACTION_STATUS_CANCELING:
        return liveaction

    if liveaction.status not in action_constants.LIVEACTION_CANCELABLE_STATES:
        raise Exception('Unable to cancel execution because it is already in a completed state.')

    result = {
        'message': 'Action canceled by user.',
        'user': requester
    }

    # There is real work only when liveaction is still running.
    status = (action_constants.LIVEACTION_STATUS_CANCELING
              if liveaction.status == action_constants.LIVEACTION_STATUS_RUNNING
              else action_constants.LIVEACTION_STATUS_CANCELED)

    update_status(liveaction, status, result=result)

    execution = ActionExecution.get(liveaction__id=str(liveaction.id))

    return (liveaction, execution)


def _cleanup_liveaction(liveaction):
    try:
        LiveAction.delete(liveaction)
    except:
        LOG.exception('Failed cleaning up LiveAction: %s.', liveaction)
        pass


def _is_notify_empty(notify_db):
    """
    notify_db is considered to be empty if notify_db is None and neither
    of on_complete, on_success and on_failure have values.
    """
    if not notify_db:
        return True
    return not (notify_db.on_complete or notify_db.on_success or notify_db.on_failure)
