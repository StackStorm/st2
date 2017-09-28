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
RUNNER_TTL = 'ttl'

DEFAULT_SCHEMA = {
    "title": "response_data",
    "type": "object",
    "properties": {
        "continue": {
            "type": "boolean",
            "description": "Would you like to continue the workflow?",
            "required": True
        }
    }
}


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
        self.schema = self.runner_parameters.get(RUNNER_SCHEMA, DEFAULT_SCHEMA)
        self.roles_param = self.runner_parameters.get(RUNNER_ROLES, [])
        self.users_param = self.runner_parameters.get(RUNNER_USERS, [])
        self.tag = self.runner_parameters.get(RUNNER_TAG, "")
        self.ttl = self.runner_parameters.get(RUNNER_TTL, 1440)

    def run(self, action_parameters):

        liveaction_db = action_utils.get_liveaction_by_id(self.liveaction_id)

        # Assemble and dispatch trigger
        trigger_ref = ResourceReference.to_string_reference(
            pack=INQUIRY_TRIGGER['pack'],
            name=INQUIRY_TRIGGER['name']
        )
        trigger_payload = {
            "id": self.liveaction_id,
            "schema": self.schema,
            "roles": self.roles_param,
            "users": self.users_param,
            "tag": self.tag,
            "ttl": self.ttl
        }
        self.trigger_dispatcher.dispatch(trigger_ref, trigger_payload)

        # We only want to request a pause if this has a parent
        if liveaction_db.context.get("parent"):

            # Get the root liveaction and request that it pauses
            root_liveaction = action_service.get_root_liveaction(liveaction_db)
            action_service.request_pause(
                root_liveaction,
                self.context.get('user', None)
            )

        result = {
            "schema": self.schema,
            "roles": self.roles_param,
            "users": self.users_param,
            "tag": self.tag,
            "ttl": self.ttl
        }
        return (LIVEACTION_STATUS_PENDING, result, None)
