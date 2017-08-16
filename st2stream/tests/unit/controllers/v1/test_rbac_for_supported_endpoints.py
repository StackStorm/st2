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

import httplib

import six

from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.rbac import UserRoleAssignmentDB

from base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'APIControllersRBACTestCase'
]


class APIControllersRBACTestCase(APIControllerWithRBACTestCase):
    """
    Test class which hits all the API endpoints which are behind the RBAC wall with a user which
    has no permissions and makes sure API returns access denied.
    """

    def setUp(self):
        super(APIControllersRBACTestCase, self).setUp()

        self.role_assignment_db_model = UserRoleAssignmentDB(user='user', role='role')
        UserRoleAssignment.add_or_update(self.role_assignment_db_model)

    def test_api_endpoints_behind_rbac_wall(self):

        supported_endpoints = [
            # Stream
            {
                'path': '/v1/stream',
                'method': 'GET'
            }
        ]

        self.use_user(self.users['no_permissions'])
        for endpoint in supported_endpoints:
            response = self._perform_request_for_endpoint(endpoint=endpoint)
            msg = '%s "%s" didn\'t return 403 status code (body=%s)' % (endpoint['method'],
                                                                        endpoint['path'],
                                                                        response.body)
            self.assertEqual(response.status_code, httplib.FORBIDDEN, msg)

    def _perform_request_for_endpoint(self, endpoint):
        if endpoint['method'] == 'GET':
            response = self.app.get(endpoint['path'], expect_errors=True)
        elif endpoint['method'] == 'POST':
            return self.app.post_json(endpoint['path'], endpoint['payload'], expect_errors=True)
        elif endpoint['method'] == 'PUT':
            return self.app.put_json(endpoint['path'], endpoint['payload'], expect_errors=True)
        elif endpoint['method'] == 'DELETE':
            return self.app.delete(endpoint['path'], expect_errors=True)
        else:
            raise ValueError('Unsupported method: %s' % (endpoint['method']))

        return response
