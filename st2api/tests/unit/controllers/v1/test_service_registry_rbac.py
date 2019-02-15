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

import six

from st2common.service_setup import register_service_in_service_registry
from st2common.services import coordination

from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'ServiceRegistryControllerRBACTestCase'
]


class ServiceRegistryControllerRBACTestCase(APIControllerWithRBACTestCase):
    @classmethod
    def setUpClass(cls):
        super(ServiceRegistryControllerRBACTestCase, cls).setUpClass()
        # Register mock service in the service registry for testing purposes
        register_service_in_service_registry(service='mock_service',
                                             capabilities={'key1': 'value1',
                                                           'name': 'mock_service'},
                                             start_heart=True)

    @classmethod
    def tearDownClass(cls):
        super(ServiceRegistryControllerRBACTestCase, cls).tearDownClass()

        coordinator = coordination.get_coordinator()
        coordination.coordinator_teardown(coordinator)

    def test_get_groups(self):
        # Non admin users can't access that API endpoint
        for user_db in [self.users['no_permissions'], self.users['observer']]:
            self.use_user(user_db)

            resp = self.app.get('/v1/service_registry/groups', expect_errors=True)
            expected_msg = ('Administrator access required')
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertEqual(resp.json['faultstring'], expected_msg)

        # Admin user can access it
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/service_registry/groups')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertEqual(resp.json, {'groups': ['mock_service']})

    def test_get_group_members(self):
        # Non admin users can't access that API endpoint
        for user_db in [self.users['no_permissions'], self.users['observer']]:
            self.use_user(user_db)

            resp = self.app.get('/v1/service_registry/groups/mock_service/members',
                                expect_errors=True)
            expected_msg = ('Administrator access required')
            self.assertEqual(resp.status_code, http_client.FORBIDDEN)
            self.assertEqual(resp.json['faultstring'], expected_msg)

        # Admin user can access it
        user_db = self.users['admin']
        self.use_user(user_db)

        resp = self.app.get('/v1/service_registry/groups/mock_service/members')
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue('members' in resp.json)
