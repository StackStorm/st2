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

from st2common.service_setup import register_service_in_service_registry
from st2common.util import system_info
from st2common.services.coordination import get_member_id
from st2common.services import coordination

from st2tests import config as tests_config

from st2tests.api import FunctionalTest

__all__ = [
    'ServiceyRegistryControllerTestCase'
]


class ServiceyRegistryControllerTestCase(FunctionalTest):

    coordinator = None

    @classmethod
    def setUpClass(cls):
        super(ServiceyRegistryControllerTestCase, cls).setUpClass()

        tests_config.parse_args(coordinator_noop=True)

        cls.coordinator = coordination.get_coordinator(use_cache=False)

        # NOTE: We mock call common_setup to emulate service being registered in the service
        # registry during bootstrap phase
        register_service_in_service_registry(service='mock_service',
                                             capabilities={'key1': 'value1',
                                                           'name': 'mock_service'},
                                             start_heart=True)

    @classmethod
    def tearDownClass(cls):
        super(ServiceyRegistryControllerTestCase, cls).tearDownClass()

        coordination.coordinator_teardown(cls.coordinator)

    def test_get_groups(self):
        list_resp = self.app.get('/v1/service_registry/groups')
        self.assertEqual(list_resp.status_int, 200)
        self.assertEqual(list_resp.json, {'groups': ['mock_service']})

    def test_get_group_members(self):
        proc_info = system_info.get_process_info()
        member_id = get_member_id()

        # 1. Group doesn't exist
        resp = self.app.get('/v1/service_registry/groups/doesnt-exist/members', expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertEqual(resp.json['faultstring'], 'Group with ID "doesnt-exist" not found.')

        # 2. Group exists and has a single member
        resp = self.app.get('/v1/service_registry/groups/mock_service/members')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'members': [
                {
                    'group_id': 'mock_service',
                    'member_id': member_id.decode('utf-8'),
                    'capabilities': {
                        'key1': 'value1',
                        'name': 'mock_service',
                        'hostname': proc_info['hostname'],
                        'pid': proc_info['pid']
                    }
                }
            ]
        })
