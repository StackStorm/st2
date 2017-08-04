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

from st2common.constants import action as action_constants
from st2common.transport import reactor
from st2common.transport import liveaction
from st2common.transport import execution
from st2common.transport import actionexecutionstate
from st2common.transport import publishers

__all__ = [
    'ACTIONSCHEDULER_REQUEST_QUEUE',

    'ACTIONRUNNER_WORK_QUEUE',
    'ACTIONRUNNER_CANCEL_QUEUE',

    'EXPORTER_WORK_QUEUE',

    'NOTIFIER_ACTIONUPDATE_WORK_QUEUE',

    'RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE',

    'RULESENGINE_WORK_QUEUE'
]

# Used by the action scheduler service
ACTIONSCHEDULER_REQUEST_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.req', routing_key=action_constants.LIVEACTION_STATUS_REQUESTED)

# Used by the action runner service
ACTIONRUNNER_WORK_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.work', routing_key=action_constants.LIVEACTION_STATUS_SCHEDULED)

ACTIONRUNNER_CANCEL_QUEUE = liveaction.get_status_management_queue(
    'st2.actionrunner.canel', routing_key=action_constants.LIVEACTION_STATUS_CANCELING)

# Used by the exporter service
EXPORTER_WORK_QUEUE = execution.get_queue(
    'st2.exporter.work', routing_key=publishers.UPDATE_RK)

# Used by the notifier service
NOTIFIER_ACTIONUPDATE_WORK_QUEUE = execution.get_queue('st2.notifiers.execution.work',
                                                       routing_key=publishers.UPDATE_RK)

# Used by the results tracker service
RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE = actionexecutionstate.get_queue('st2.resultstracker.work',
    routing_key=publishers.CREATE_RK)

# Used by the rules engine service
RULESENGINE_WORK_QUEUE = reactor.get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine', routing_key='#')
