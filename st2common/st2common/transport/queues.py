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

"""
Module containing constants for all the statically named queue.

They are located inside this module so they can be referenced inside multiple places without
encountering cylic import issues.
"""

from __future__ import absolute_import

from kombu import Queue

from st2common.constants import action as action_constants
from st2common.transport import actionexecutionstate
from st2common.transport import announcement
from st2common.transport import execution
from st2common.transport import liveaction
from st2common.transport import publishers
from st2common.transport import reactor
from st2common.transport import workflow

__all__ = [
    'ACTIONSCHEDULER_REQUEST_QUEUE',

    'ACTIONRUNNER_WORK_QUEUE',
    'ACTIONRUNNER_CANCEL_QUEUE',
    'ACTIONRUNNER_PAUSE_QUEUE',
    'ACTIONRUNNER_RESUME_QUEUE',

    'EXPORTER_WORK_QUEUE',

    'NOTIFIER_ACTIONUPDATE_WORK_QUEUE',

    'RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE',

    'RULESENGINE_WORK_QUEUE',

    'STREAM_ANNOUNCEMENT_WORK_QUEUE',
    'STREAM_EXECUTION_ALL_WORK_QUEUE',
    'STREAM_EXECUTION_UPDATE_WORK_QUEUE',
    'STREAM_LIVEACTION_WORK_QUEUE',

    'WORKFLOW_EXECUTION_WORK_QUEUE',
    'WORKFLOW_EXECUTION_RESUME_QUEUE'
]


# Used by the action scheduler service
ACTIONSCHEDULER_REQUEST_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.req',
    routing_key=action_constants.LIVEACTION_STATUS_REQUESTED)


# Used by the action runner service
ACTIONRUNNER_WORK_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.work',
    routing_key=action_constants.LIVEACTION_STATUS_SCHEDULED)

ACTIONRUNNER_CANCEL_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.cancel',
    routing_key=action_constants.LIVEACTION_STATUS_CANCELING)

ACTIONRUNNER_PAUSE_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.pause',
    routing_key=action_constants.LIVEACTION_STATUS_PAUSING)

ACTIONRUNNER_RESUME_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.resume',
    routing_key=action_constants.LIVEACTION_STATUS_RESUMING)


# Used by the exporter service
EXPORTER_WORK_QUEUE = execution.get_queue(
    'st2.exporter.work',
    routing_key=publishers.UPDATE_RK)


# Used by the notifier service
NOTIFIER_ACTIONUPDATE_WORK_QUEUE = execution.get_queue(
    'st2.notifiers.execution.work',
    routing_key=publishers.UPDATE_RK)


# Used by the results tracker service
RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE = actionexecutionstate.get_queue(
    'st2.resultstracker.work',
    routing_key=publishers.CREATE_RK)


# Used by the rules engine service
RULESENGINE_WORK_QUEUE = reactor.get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine',
    routing_key='#')


# Used by the stream service
STREAM_ANNOUNCEMENT_WORK_QUEUE = announcement.get_queue(
    routing_key=publishers.ANY_RK,
    exclusive=True,
    auto_delete=True)

STREAM_EXECUTION_ALL_WORK_QUEUE = execution.get_queue(
    routing_key=publishers.ANY_RK,
    exclusive=True,
    auto_delete=True)

STREAM_EXECUTION_UPDATE_WORK_QUEUE = execution.get_queue(
    routing_key=publishers.UPDATE_RK,
    exclusive=True,
    auto_delete=True)

STREAM_LIVEACTION_WORK_QUEUE = Queue(
    None,
    liveaction.LIVEACTION_XCHG,
    routing_key=publishers.ANY_RK,
    exclusive=True,
    auto_delete=True)

# TODO: Perhaps we should use pack.action name as routing key
# so we can do more efficient filtering later, if needed
STREAM_EXECUTION_OUTPUT_QUEUE = execution.get_output_queue(
    name=None,
    routing_key=publishers.CREATE_RK,
    exclusive=True,
    auto_delete=True)


# Used by the workflow engine service
WORKFLOW_EXECUTION_WORK_QUEUE = workflow.get_queue(
    name='st2.workflow.work',
    routing_key=publishers.CREATE_RK)

WORKFLOW_EXECUTION_RESUME_QUEUE = workflow.get_status_management_queue(
    name='st2.workflow.resume',
    routing_key=action_constants.LIVEACTION_STATUS_RESUMING)
