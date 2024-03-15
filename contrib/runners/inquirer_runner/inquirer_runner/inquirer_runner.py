# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import uuid

from st2common import log as logging
from st2common.constants import action as action_constants
from st2common.constants import triggers as trigger_constants
from st2common.models.system import common as sys_db_models
from st2common.persistence import execution as ex_db_access
from st2common.runners import base as runners
from st2common.services import action as action_service
from st2common.services import workflows as workflow_service
from st2common.transport import reactor as reactor_transport
from st2common.util import action_db as action_utils


__all__ = ["Inquirer", "get_runner", "get_metadata"]

LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters.
RUNNER_SCHEMA = "schema"
RUNNER_ROLES = "roles"
RUNNER_USERS = "users"
RUNNER_ROUTE = "route"
RUNNER_TTL = "ttl"

DEFAULT_SCHEMA = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "continue": {
            "type": "boolean",
            "description": "Would you like to continue the workflow?",
            "required": True,
        }
    },
}


class Inquirer(runners.ActionRunner):
    """This runner implements the ability to ask for more input during a workflow"""

    def __init__(self, runner_id):
        super(Inquirer, self).__init__(runner_id=runner_id)
        self.trigger_dispatcher = reactor_transport.TriggerDispatcher(LOG)

    def pre_run(self):
        super(Inquirer, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self.schema = self.runner_parameters.get(RUNNER_SCHEMA, DEFAULT_SCHEMA)
        self.roles_param = self.runner_parameters.get(RUNNER_ROLES, [])
        self.users_param = self.runner_parameters.get(RUNNER_USERS, [])
        self.route = self.runner_parameters.get(RUNNER_ROUTE, "")
        self.ttl = self.runner_parameters.get(RUNNER_TTL, 1440)

    def run(self, action_parameters):
        liveaction_db = action_utils.get_liveaction_by_id(self.liveaction_id)
        exc = ex_db_access.ActionExecution.get(liveaction__id=str(liveaction_db.id))

        # Assemble and dispatch trigger
        trigger_ref = sys_db_models.ResourceReference.to_string_reference(
            pack=trigger_constants.INQUIRY_TRIGGER["pack"],
            name=trigger_constants.INQUIRY_TRIGGER["name"],
        )

        trigger_payload = {"id": str(exc.id), "route": self.route}

        self.trigger_dispatcher.dispatch(trigger_ref, trigger_payload)

        result = {
            "schema": self.schema,
            "roles": self.roles_param,
            "users": self.users_param,
            "route": self.route,
            "ttl": self.ttl,
        }

        return (action_constants.LIVEACTION_STATUS_PENDING, result, None)

    def post_run(self, status, result):
        # If the action execution goes into pending state at the onstart of the inquiry,
        # then paused the parent/root workflow in the post run. Previously, the pause request
        # is made in the run method, but because the liveaction hasn't update to pending status
        # yet, there is a race condition where the pause request is mishandled.
        if status == action_constants.LIVEACTION_STATUS_PENDING:
            pause_parent = self.liveaction.context.get(
                "parent"
            ) and not workflow_service.is_action_execution_under_workflow_context(
                self.liveaction
            )

            # For action execution under Action Chain workflows, request the entire
            # workflow to pause. Orquesta handles pause differently and so does not require parent
            # to pause. Orquesta allows for other branches to keep running. When there is no other
            # active branches, the conductor will see there is only the pending task and will know
            # to pause the workflow.
            if pause_parent:
                root_liveaction = action_service.get_root_liveaction(self.liveaction)
                action_service.request_pause(
                    root_liveaction, self.context.get("user", None)
                )

        # Invoke post run of parent for common post run related work.
        super(Inquirer, self).post_run(status, result)


def get_runner():
    return Inquirer(str(uuid.uuid4()))


def get_metadata():
    return runners.get_metadata("inquirer_runner")[0]
