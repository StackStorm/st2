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

import datetime
import six

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.actionrunner import ActionRunnerException
from st2common.persistence.action import LiveAction
from st2common.persistence.execution import ActionExecution
from st2common.services import executions
from st2common.util import isotime, system_info
from st2common.util import action_db as action_utils
from st2common.util import schema as util_schema


__all__ = [
    'schedule',
    'execute',
    'is_action_canceled'
]

LOG = logging.getLogger(__name__)


def _get_immutable_params(parameters):
    if not parameters:
        return []
    return [k for k, v in six.iteritems(parameters) if v.get('immutable', False)]


def schedule(liveaction):
    """
    Schedule an action to be run.

    :return: (liveaction, execution)
    :rtype: tuple
    """
    # Use the user context from the parent action execution. Subtasks in a workflow
    # action can be invoked by a system user and so we want to use the user context
    # from the original workflow action.
    if getattr(liveaction, 'context', None) and 'parent' in liveaction.context:
        parent = LiveAction.get_by_id(liveaction.context['parent'])
        liveaction.context['user'] = getattr(parent, 'context', dict()).get('user')

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
    schema = util_schema.get_parameter_schema(action_db)
    validator = util_schema.get_validator()
    util_schema.validate(liveaction.parameters, schema, validator, use_default=True)

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
    if action_db.notify:
        liveaction.notify = action_db.notify

    # Write to database and send to message queue.
    liveaction.status = action_constants.LIVEACTION_STATUS_SCHEDULED
    liveaction.start_timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
    # Publish creation after both liveaction and actionexecution are created.
    liveaction = LiveAction.add_or_update(liveaction, publish=False)
    execution = executions.create_execution_object(liveaction, publish=False)
    # assume that this is a creation.
    LiveAction.publish_create(liveaction)
    ActionExecution.publish_create(execution)

    extra = {'liveaction_db': liveaction, 'execution_db': execution}
    LOG.audit('Action execution scheduled. LiveAction.id=%s, ActionExecution.id=%s' %
              (liveaction.id, execution.id), extra=extra)
    return liveaction, execution


def execute(liveaction, container):
    """
    Execute an action.

    :return: result
    :rtype: dict
    """
    # Only execution actions which haven't completed yet.
    if liveaction.status == action_constants.LIVEACTION_STATUS_CANCELED:
        LOG.info('Not executing liveaction %s. User canceled execution.', liveaction.id)
        if not liveaction.result:
            action_utils.update_liveaction_status(
                status=action_constants.LIVEACTION_STATUS_CANCELED,
                result={'message': 'Action execution canceled by user.'},
                liveaction_id=liveaction.id)
        return

    if liveaction.status in [action_constants.LIVEACTION_STATUS_SUCCEEDED,
                             action_constants.LIVEACTION_STATUS_FAILED]:
        LOG.info('Ignoring liveaction %s which has already finished.', liveaction.id)
        return

    try:
        liveaction_db = action_utils.get_liveaction_by_id(liveaction.id)
    except StackStormDBObjectNotFoundError:
        LOG.exception('Failed to find liveaction %s in the database.',
                      liveaction.id)
        raise

    # stamp liveaction with process_info
    runner_info = system_info.get_process_info()

    # Update liveaction status to "running"
    liveaction_db = action_utils.update_liveaction_status(
        status=action_constants.LIVEACTION_STATUS_RUNNING,
        runner_info=runner_info,
        liveaction_id=liveaction_db.id)
    action_execution_db = executions.update_execution(liveaction_db)

    # Launch action
    extra = {'action_execution_db': action_execution_db, 'liveaction_db': liveaction_db}
    LOG.audit('Launching action execution.', extra=extra)

    # the extra field will not be shown in non-audit logs so temporarily log at info.
    LOG.info('{~}action_execution: %s / {~}live_action: %s',
             action_execution_db.id, liveaction_db.id)
    try:
        result = container.dispatch(liveaction_db)
        LOG.debug('Runner dispatch produced result: %s', result)
        if not result:
            raise ActionRunnerException('Failed to execute action.')
    except Exception:
        liveaction_db = action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_FAILED,
            liveaction_id=liveaction_db.id)

        raise

    return result


def is_action_canceled(liveaction_id):
    liveaction_db = action_utils.get_liveaction_by_id(liveaction_id)
    return liveaction_db.status == action_constants.LIVEACTION_STATUS_CANCELED
