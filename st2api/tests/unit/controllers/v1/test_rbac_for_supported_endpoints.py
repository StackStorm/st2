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
    'aliases': ['alias1.yaml'],
    'rules': ['rule1.yaml'],
    'triggers': ['trigger1.yaml'],
    'triggertypes': ['triggertype1.yaml'],
    'executions': ['execution1.yaml'],
    'liveactions': ['liveaction1.yaml', 'parentliveaction.yaml', 'childliveaction.yaml'],
    'enforcements': ['enforcement1.yaml']
}

MOCK_RUNNER_1 = {
    'name': 'test-runner-1',
    'description': 'test',
    'enabled': False
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

MOCK_ACTION_ALIAS_1 = {
    'name': 'alias3',
    'pack': 'aliases',
    'description': 'test description',
    'action_ref': 'core.local',
    'formats': ['a', 'b']
}

MOCK_RULE_1 = {
    'enabled': True,
    'name': 'st2.test.rule2',
    'pack': 'yoyohoneysingh',
    'trigger': {
        'type': 'wolfpack.triggertype-1'
    },
    'criteria': {
        'trigger.k1': {
            'pattern': 't1_p_v',
            'type': 'equals'
        }
    },
    'action': {
        'ref': 'sixpack.st2.test.action',
        'parameters': {
            'ip2': '{{rule.k1}}',
            'ip1': '{{trigger.t1_p}}'
        }
    },
    'description': ''
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

        # Insert mock objects - those objects are used to test get one, edit and delete operations
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

    def test_api_endpoints_behind_rbac_wall(self):
        #  alias_model = self.models['aliases']['alias1.yaml']
        sensor_model = self.models['sensors']['sensor1.yaml']
        rule_model = self.models['rules']['rule1.yaml']
        enforcement_model = self.models['enforcements']['enforcement1.yaml']
        execution_model = self.models['executions']['execution1.yaml']

        supported_endpoints = [
            # Runners
            {
                'path': '/v1/runnertypes',
                'method': 'GET'
            },
            {
                'path': '/v1/runnertypes/test-runner-1',
                'method': 'GET'
            },
            {
                'path': '/v1/runnertypes/test-runner-1',
                'method': 'PUT',
                'payload': MOCK_RUNNER_1
            },
            # Packs
            {
                'path': '/v1/packs',
                'method': 'GET'
            },
            {
                'path': '/v1/packs/dummy_pack_1',
                'method': 'GET'
            },
            # Pack views
            {
                'path': '/v1/packs/views/files/dummy_pack_1',
                'method': 'GET'
            },
            # Pack config schemas
            {
                'path': '/v1/config_schemas',
                'method': 'GET'
            },
            {
                'path': '/v1/config_schemas/dummy_pack_1',
                'method': 'GET'
            },
            {
                'path': '/v1/packs/views/file/dummy_pack_1/pack.yaml',
                'method': 'GET'
            },
            # Sensors
            {
                'path': '/v1/sensortypes',
                'method': 'GET'
            },
            {
                'path': '/v1/sensortypes/%s' % (sensor_model.ref),
                'method': 'GET'
            },
            {
                'path': '/v1/sensortypes/%s' % (sensor_model.ref),
                'method': 'PUT',
                'payload': {'enabled': False}
            },
            # Actions
            {
                'path': '/v1/actions',
                'method': 'GET'
            },
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
            },
            # Action aliases
            {
                'path': '/v1/actionalias',
                'method': 'GET'
            },
            {
                'path': '/v1/actionalias/aliases.alias1',
                'method': 'GET'
            },
            {
                'path': '/v1/actionalias',
                'method': 'POST',
                'payload': MOCK_ACTION_ALIAS_1
            },
            {
                'path': '/v1/actionalias/aliases.alias1',
                'method': 'PUT',
                'payload': MOCK_ACTION_ALIAS_1
            },
            {
                'path': '/v1/actionalias/aliases.alias1',
                'method': 'DELETE'
            },
            # Rules
            {
                'path': '/v1/rules',
                'method': 'GET'
            },
            {
                'path': '/v1/rules/%s' % (rule_model.ref),
                'method': 'GET'
            },
            {
                'path': '/v1/rules',
                'method': 'POST',
                'payload': MOCK_RULE_1
            },
            {
                'path': '/v1/rules/%s' % (rule_model.ref),
                'method': 'PUT',
                'payload': {'enabled': False}
            },
            {
                'path': '/v1/rules/%s' % (rule_model.ref),
                'method': 'DELETE'
            },
            # Rule enforcements
            {
                'path': '/v1/ruleenforcements',
                'method': 'GET'
            },
            {
                'path': '/v1/ruleenforcements/%s' % (enforcement_model.id),
                'method': 'GET'
            },
            # Action Executions
            {
                'path': '/v1/executions',
                'method': 'GET'
            },
            {
                'path': '/v1/executions/%s' % (execution_model.id),
                'method': 'GET'
            },
            {
                'path': '/v1/executions',
                'method': 'POST',
                'payload': {'action': 'core.local'}  # schedule execution / run action
            },
            {
                'path': '/v1/executions/%s' % (execution_model.id),
                'method': 'DELETE'  # stop execution
            },
            {
                'path': '/v1/executions/%s/re_run' % (execution_model.id),
                'method': 'POST',  # re-run execution
                'payload': {'parameters': {}}
            },
            # Action execution nested controllers
            {
                'path': '/v1/executions/%s/attribute/trigger_instance' % (execution_model.id),
                'method': 'GET'
            },
            {
                'path': '/v1/executions/%s/children' % (execution_model.id),
                'method': 'GET'
            },
            # Alias executions
            {
                'path': '/v1/aliasexecution',
                'method': 'POST',
                'payload': {'name': 'alias1', 'format': 'foo bar ponies',
                            'command': 'foo bar ponies',
                            'user': 'channel', 'source_channel': 'bar'}
            }
        ]

        self.use_user(self.users['no_permissions'])
        for endpoint in supported_endpoints:
            response = self._perform_request_for_endpoint(endpoint=endpoint)
            msg = '%s "%s" didn\'t return 403 status code (body=%s)' % (endpoint['method'],
                                                                        endpoint['path'],
                                                                        response.body)
            self.assertEqual(response.status_code, httplib.FORBIDDEN, msg)

    def test_icon_png_file_is_whitelisted(self):
        self.use_user(self.users['no_permissions'])

        # Test that access to icon.png file doesn't require any permissions
        # Note: We need to mock content-type since pecan and webest don't like if content-type is
        # set dynamically in the request handler aka  "pecan.core: ERROR: Controller 'get_one'
        # defined does not support content_type 'image/png'. Supported type(s): ['text/html']" is
        # returned
        from st2api.controllers.v1.packviews import FileController
        FileController.get_one._pecan['content_types'] = {'image/png': None}
        FileController.get_one._pecan['explicit_content_type'] = True

        response = self.app.get('/v1/packs/views/file/dummy_pack_2/icon.png')
        self.assertEqual(response.status_code, httplib.OK)

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
