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

from st2api.controllers.resource import ResourceController
from st2common import log as logging
from st2common.util import action_db as action_utils
from st2common.util import system_info
from st2common.services import executions
from st2common.rbac.types import PermissionType
from st2common.rbac import utils as rbac_utils
from st2common.models.api.execution import ActionExecutionAPI
from st2common.persistence.execution import ActionExecution

__all__ = [
    'InquiriesController'
]

LOG = logging.getLogger(__name__)


test_schema = {
    "type": "object",
    "required": [
        'approval'
    ],
    "properties": {
        "approval": {
            "description": "",
            "type": "boolean"
        }
    }
}

test_inquiries = [
    {
        "id": "abcdef",
        "parent": "aaaaaa",
        "response_schema": test_schema,
        "tag": "developers",
        "users": ["mierdin", "st2admin"],
        "roles": []
    },
    {
        "id": "123456",
        "parent": "111111",
        "response_schema": test_schema,
        "tag": "ops",
        "users": [],
        "roles": ["admins"]
    }
]


class InquiriesController(ResourceController):
    """Everything in this controller is just a PoC at this point. Just getting my feet wet and
       using dummy data before diving into the actual back-end queries.
    """
    supported_filters = {}

    # No data model currently exists for Inquiries, so we're "borrowing" ActionExecutions
    model = ActionExecutionAPI
    access = ActionExecution

    def get_all(self, requester_user=None):

        # Basically, get all ActionExecutions with a `pending` status.

        return test_inquiries

    def get_one(self, iid, requester_user=None):

        # Should be identical to getting an execution by ID, only with different fields.

        return [i for i in test_inquiries if i["id"] == iid][0]

    def put(self, iid, rdata, requester_user):
        """
        This function in particular will:

        1. Retrieve details of the inquiry via ID (i.e. params like schema)
        2. Determine permission of this user to respond to this Inquiry
        3. Validate the body of the response against the schema parameter for this inquiry,
           (reject if invalid)
        4. Update inquiry's execution result with a successful status and the validated response
        5. Retrieve parent execution for the inquiry, and pass this to action_service.request_resume

        """

        #
        # Retrieve details of the inquiry via ID (i.e. params like schema)
        #
        existing_inquiry = self._get_one_by_id(
            id=iid,
            requester_user=requester_user,
            permission_type=PermissionType.EXECUTION_VIEW
        )
        LOG.info("Got existing inquiry ID: %s" % existing_inquiry.id)

        #
        # Determine permission of this user to respond to this Inquiry
        #
        if not requester_user:
                # TODO(mierdin) figure out how to return this in an HTTP code
                # (and modify the openapi def accordingly)
            raise Exception("Not permitted")
        roles = existing_inquiry.parameters.get('roles')
        users = existing_inquiry.parameters.get('users')
        if roles:
            for role in roles:
                LOG.info("Checking user %s is in role %s" % (requester_user, role))
                LOG.info(rbac_utils.user_has_role(requester_user, role))
                # TODO(mierdin): Note that this will always return True if Rbac is not enabled
                # Need to test with rbac enabled and configured
                if rbac_utils.user_has_role(requester_user, role):
                    break
            else:
                # TODO(mierdin) figure out how to return this in an HTTP code
                # (and modify the openapi def accordingly)
                raise Exception("Not permitted")
        if users:
            if requester_user not in users:
                # TODO(mierdin) figure out how to return this in an HTTP code
                # (and modify the openapi def accordingly)
                raise Exception("Not permitted")

        #
        # Validate the body of the response against the schema parameter for this inquiry,
        #

        #
        # Update inquiry's execution result with a successful status and the validated response
        #
        # # stamp liveaction with process_info
        # runner_info = system_info.get_process_info()
        # # Update liveaction status to "running"
        # liveaction_db = action_utils.update_liveaction_status(
        #     status=action_constants.LIVEACTION_STATUS_RUNNING,
        #     runner_info=runner_info,
        #     liveaction_id=liveaction_db.id)
        # self._running_liveactions.add(liveaction_db.id)
        # action_execution_db = executions.update_execution(liveaction_db)

        # return "Received data for inquiry %s" % id

        response_data = getattr(rdata, 'response_data')

        return {
            "id": iid,
            "response_data": response_data
        }


inquiries_controller = InquiriesController()
