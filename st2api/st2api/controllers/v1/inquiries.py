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


class InquiriesController(ResourceController):

    def get_all(self):
        pass

    def get_one(self):
        pass

    def put(self, id, liveaction_api, requester_user, show_secrets=False):
        """
        Things to implement in this function:

        1. Retrieve details of the inquiry via ID (i.e. params like schema)
        2. Get current roles of which `requester_user` is a member (if any)
        3. Compare params of inquiry with roles of current user, reject if not allowed to respond
        4. Validate the body of the response against the schema parameter for this inquiry,
           (reject if invalid)
        5. Update inquiry's execution result with a successful status and the validated response
        6. Retrieve parent execution for the inquiry, and pass this to action_service.request_resume

        """
        pass


inquiries_controller = InquiriesController()
