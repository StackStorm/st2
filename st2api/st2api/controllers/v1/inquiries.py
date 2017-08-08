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

__all__ = [
    'InquiriesController'
]

LOG = logging.getLogger(__name__)


test_inquiries = [
    {
        "id": "abcdef",
        "params": {
            "tag": "developers",
            "users": [],
            "roles": []
        }
    },
    {
        "id": "123456",
        "params": {
            "tag": "ops",
            "users": [],
            "roles": []
        }
    }
]


class InquiriesController(ResourceController):
    """Everything in this controller is just a PoC at this point. Just getting my feet wet and
       using dummy data before diving into the actual back-end queries.
    """
    supported_filters = {}
    model = None
    access = None

    def get_all(self, requester_user=None):
        return [test_inquiries]

    def get_one(self, id, requester_user=None):
        return [i for i in test_inquiries if i["id"] == id][0]

    def put(self, id, requester_user=None):
        """
        This function in particular will:

        1. Retrieve details of the inquiry via ID (i.e. params like schema)
        2. Get current roles of which `requester_user` is a member (if any)
        3. Compare params of inquiry with roles of current user, reject if not allowed to respond
        4. Validate the body of the response against the schema parameter for this inquiry,
           (reject if invalid)
        5. Update inquiry's execution result with a successful status and the validated response
        6. Retrieve parent execution for the inquiry, and pass this to action_service.request_resume

        """
        return "Received data for inquiry %s" % id


inquiries_controller = InquiriesController()
