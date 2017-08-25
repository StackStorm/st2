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

import uuid

from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_PENDING
from st2common.constants.triggers import INQUIRY_TRIGGER
from st2common.models.system.common import ResourceReference
from st2common.persistence.execution import ActionExecution
from st2common.persistence.liveaction import LiveAction
from st2common.runners.base import ActionRunner
from st2common.services import action as action_service
from st2common.transport.reactor import TriggerDispatcher
from st2common.util import action_db as action_utils

LOG = logging.getLogger(__name__)

__all__ = [
    'get_runner',
    'Inquirer',
]

# constants to lookup in runner_parameters.
RUNNER_SCHEMA = 'schema'
RUNNER_ROLES = 'roles'
RUNNER_USERS = 'users'
RUNNER_TAG = 'tag'


def get_runner():
    return Inquirer(str(uuid.uuid4()))


class Inquirer(ActionRunner):
    """This runner implements the ability to ask for more input during a workflow
    """

    def __init__(self, runner_id):
        super(Inquirer, self).__init__(runner_id=runner_id)
        self.trigger_dispatcher = TriggerDispatcher(LOG)

    def pre_run(self):
        super(Inquirer, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self.schema = self.runner_parameters.get(RUNNER_SCHEMA, None)
        self.roles_param = self.runner_parameters.get(RUNNER_ROLES, None)
        self.users_param = self.runner_parameters.get(RUNNER_USERS, None)
        self.tag = self.runner_parameters.get(RUNNER_TAG, None)

    def run(self, action_parameters):

        liveaction_db = action_utils.get_liveaction_by_id(self.liveaction_id)

        # Retrieve existing response data
        response_data = liveaction_db.result.get("response", {})

        # Assemble and dispatch trigger
        trigger_ref = ResourceReference.to_string_reference(
            pack=INQUIRY_TRIGGER['pack'],
            name=INQUIRY_TRIGGER['name']
        )
        trigger_payload = {
            "id": self.liveaction_id,
            "response": response_data,
            "schema": self.schema,
            "roles": self.roles_param,
            "users": self.users_param,
            "tag": self.tag
        }
        self.trigger_dispatcher.dispatch(trigger_ref, trigger_payload)

        # Request pause if parent execution exists (workflow)
        parent = liveaction_db.context.get("parent")
        if parent:
            parent_execution = ActionExecution.get(id=parent['execution_id'])
            action_service.request_pause(
                LiveAction.get(id=parent_execution.liveaction['id']),
                self.context.get('user', None)
            )

        return (LIVEACTION_STATUS_PENDING, {"response": response_data}, None)
