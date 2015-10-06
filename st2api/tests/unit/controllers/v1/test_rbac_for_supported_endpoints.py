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

import mock
import six
import pecan

from st2common.transport.publishers import PoolPublisher
from st2common.rbac.types import PermissionType
from st2common.rbac.types import ResourceType
from st2common.persistence.auth import User
from st2common.persistence.rbac import Role
from st2common.persistence.rbac import UserRoleAssignment
from st2common.persistence.rbac import PermissionGrant
from st2common.models.db.auth import UserDB
from st2common.models.db.rbac import RoleDB
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.models.db.rbac import PermissionGrantDB
from st2tests.fixturesloader import FixturesLoader
from tests.base import APIControllerWithRBACTestCase

http_client = six.moves.http_client

__all__ = [
    'APIControllersRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'sensors': ['sensor1.yaml'],
    'actions': ['action1.yaml', 'local.yaml'],
}
MOCK_ACTION_1 = {
    'name': 'ma.dummy.action',
    'pack': 'examples',
    'description': 'test description',
    'enabled': True,
    'entry_point': '/tmp/test/action2.py',
    'runner_type': 'local-shell-script',
    'parameters': {
        'c': {'type': 'string', 'default': 'C1', 'position': 0},
        'd': {'type': 'string', 'default': 'D1', 'immutable': True}
    }
}

class APIControllersRBACTestCase(APIControllerWithRBACTestCase):
    """
    Test class which hits all the API endpoints which are behind the RBAC wall with a user which
    has no permissions and makes sure API returns access denied.
    """

    register_packs = True
    fixtures_loader = FixturesLoader()

    def setUp(self):
        super(APIControllersRBACTestCase, self).setUp()

        # Register packs
        if self.register_packs:
            self._register_packs()

        self.users = {}

        # Users
        user_1_db = UserDB(name='no_permissions')
        user_1_db = User.add_or_update(user_1_db)
        self.users['no_permissions'] = user_1_db

        # Insert mock objects - those objects are used to test get one, edit and delete operations
        print self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)

    def test_api_endpoints_behind_rbac_wall(self):
        supported_endpoints = [
            # Sensors
            #{
            #    'path': '/v1/sensors',
            #    'method': 'GET'
            #}
            {
                'path': '/v1/sensortypes/generic.sensor1',
                'method': 'GET'
            },
            # Actions
            #{
            #    'path': '/v1/actions',
            #    'method': 'GET'
            #},
            {
                'path': '/v1/actions/wolfpack.action-1',
                'method': 'GET'
            },
            {
                'path': '/v1/actions',
                'method': 'POST',
                'payload': MOCK_ACTION_1
            },
            {
                'path': '/v1/actions/wolfpack.action-1',
                'method': 'PUT',
                'payload': MOCK_ACTION_1
            },
            {
                'path': '/v1/actions/wolfpack.action-1',
                'method': 'DELETE'
            }

        ]

        self.use_user(self.users['no_permissions'])
        for endpoint in supported_endpoints:
            print endpoint['path'], endpoint['method']
            response = self._perform_request_for_endpoint(endpoint=endpoint)
            self.assertEqual(response.status_code, httplib.FORBIDDEN, endpoint['path'])

    def test_icon_png_file_is_whitelisted(self):
        self.use_user(self.users['no_permissions'])

        # Test that access to icon.png file doesn't require any permissions
        # TODO: This doesn't work since controler returns icon/png content-type
        #setattr(type(pecan.request), 'content_type', 'a/a')
        #response = self.app.get('/v1/packs/views/file/dummy_pack_2/icon.png',
        #                        expect_errors=True)
        #self.assertEqual(response.status_code, httplib.OK)

        # Other files should return forbidden
        response = self.app.get('/v1/packs/views/file/dummy_pack_2/pack.yaml',
                                expect_errors=True)
        self.assertEqual(response.status_code, httplib.FORBIDDEN)

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
