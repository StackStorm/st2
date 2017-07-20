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

import os
import uuid

from st2common import log as logging
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_PENDING  #TODO(mierdin): Need to implement this
from st2common.runners.base import ActionRunner
from st2common.runners import python_action_wrapper
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

BASE_DIR = os.path.dirname(os.path.abspath(python_action_wrapper.__file__))


def get_runner():
    'RunnerTestCase',
    return Inquirer(str(uuid.uuid4()))


class Inquirer(ActionRunner):
    """ This runner is responsible for handling st2.ask actions (i.e. can return "pending" status)

    This approach gives safer access to setting execution status and examining data in context
    """

    def __init__(self, runner_id):
        super(Inquirer, self).__init__(runner_id=runner_id)

    def pre_run(self):
        super(Inquirer, self).pre_run()

        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._schema = self.runner_parameters.get(RUNNER_SCHEMA, self._schema)
        self._roles_param = self.runner_parameters.get(RUNNER_ROLES, self._roles_param)
        self._users_param = self.runner_parameters.get(RUNNER_USERS, self._users_param)

        # Probably not needed, since this isn't used in the runner or action
        # self._tag = self.runner_parameters.get(RUNNER_TAG, self._tag)

    def run(self, action_parameters):
        """This runner provides the bulk of the implementation for st2.ask.

        The high-level steps are:

        1. Retrieve response data and JSONschema from parameters
        2. Ensure the current user has permission to provide a response
           (based off of provided "users" and "roles" params)
        3. Validate respond data against provided schema
        4. Return appropriate status based on validation
        """

        # NOTE - I am using self.context for storing the response data right now. I know there was
        # some discussion about using response instead; I'm just not quite sure how that would work
        # atm, and I think Lakshmi also had some concerns about this. So I can flex here, just doing
        # this for now.
        response_data = self.context.get("response_data")
        #
        # WIP - use result instead
        # liveaction_db = action_utils.get_liveaction_by_id(liveaction.id)
        # response_data = liveaction_db.result.get("response_data")

        # Determine if the currently authenticated user is allowed to provide a response
        if not self.has_permission():
            LOG.debug('Current user not permitted to respond to this execution.')  #TODO(mierdin): Could probably use more detail
            return (LIVEACTION_STATUS_PENDING, response_data)

        # Validate response against provided schema.
        # If valid, set status to success. If not valid, set status to pending.
        # Return this status as well as response data
        if self.validate_data(self.schema, response_data):
            return (LIVEACTION_STATUS_SUCCEEDED, response_data)
        else:
            return (LIVEACTION_STATUS_PENDING, response_data)

    def has_permission(self):
        """Determine if the current user has permission to respond to the action execution
        """

        # Grant permission if users and roles list is empty
        if not self._users_param and not self._roles_param:
            return True

        current_user = self.get_user()
        roles = get_roles_for_user(current_user)  # Just made this function name up for now

        # Grant permission if user is in provided list
        if current_user in self._users_param:
            return True

        # Grant permission if user is in one of the provided roles
        for role in roles:
            if role in self._roles_param:
                return True

        return False

    def validate_data(self, schema, response_data):
        """Perform JSONschema validation against the response data using the provided
           schema
        """
        pass
