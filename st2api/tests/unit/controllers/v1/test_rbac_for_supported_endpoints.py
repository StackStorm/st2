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

from collections import OrderedDict

import six
import mock

from st2common.services import triggers as trigger_service
with mock.patch.object(trigger_service, 'create_trigger_type_db', mock.MagicMock()):
    from st2api.controllers.v1.webhooks import HooksHolder
from st2common.persistence.rbac import UserRoleAssignment
from st2common.models.db.rbac import UserRoleAssignmentDB
from st2common.service_setup import register_service_in_service_registry
from st2common.services import coordination

from st2tests import config as tests_config
from st2tests.fixturesloader import FixturesLoader

from st2tests.api import APIControllerWithRBACTestCase
from tests.unit.controllers.v1.test_webhooks import DUMMY_TRIGGER_DICT

http_client = six.moves.http_client

__all__ = [
    'APIControllersRBACTestCase'
]

FIXTURES_PACK = 'generic'
TEST_FIXTURES = OrderedDict([
    ('runners', ['testrunner1.yaml', 'run-local.yaml']),
    ('sensors', ['sensor1.yaml']),
    ('actions', ['action1.yaml', 'local.yaml']),
    ('aliases', ['alias1.yaml']),
    ('triggers', ['trigger1.yaml', 'cron1.yaml']),
    ('rules', ['rule1.yaml']),
    ('triggertypes', ['triggertype1.yaml']),
    ('executions', ['execution1.yaml']),
    ('liveactions', ['liveaction1.yaml', 'parentliveaction.yaml', 'childliveaction.yaml']),
    ('enforcements', ['enforcement1.yaml']),
    ('apikeys', ['apikey1.yaml']),
    ('traces', ['trace_for_test_enforce.yaml'])
])

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

    coordinator = None

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args(coordinator_noop=True)

        super(APIControllersRBACTestCase, cls).setUpClass()

        cls.coordinator = coordination.get_coordinator(use_cache=False)

        # Register mock service in the service registry for testing purposes
        service = six.binary_type(six.text_type('mock_service').encode('ascii'))
        register_service_in_service_registry(service=service,
                                             capabilities={'key1': 'value1',
                                                           'name': 'mock_service'},
                                             start_heart=True)

    @classmethod
    def tearDownClass(cls):
        super(APIControllersRBACTestCase, cls).tearDownClass()

        coordination.coordinator_teardown(cls.coordinator)

    def setUp(self):
        super(APIControllersRBACTestCase, self).setUp()

        # Register packs
        if self.register_packs:
            self._register_packs()

        # Insert mock objects - those objects are used to test get one, edit and delete operations
        self.models = self.fixtures_loader.save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                               fixtures_dict=TEST_FIXTURES)

        self.role_assignment_db_model = UserRoleAssignmentDB(
            user='user', role='role', source='assignments/user.yaml')
        UserRoleAssignment.add_or_update(self.role_assignment_db_model)

    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    def test_api_endpoints_behind_rbac_wall(self):
        #  alias_model = self.models['aliases']['alias1.yaml']
        sensor_model = self.models['sensors']['sensor1.yaml']
        rule_model = self.models['rules']['rule1.yaml']
        enforcement_model = self.models['enforcements']['enforcement1.yaml']
        execution_model = self.models['executions']['execution1.yaml']
        trace_model = self.models['traces']['trace_for_test_enforce.yaml']
        timer_model = self.models['triggers']['cron1.yaml']

        supported_endpoints = [
            # Runners
            {
                'path': '/v1/runnertypes',
                'method': 'GET',
                'is_getall': True
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
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/packs/dummy_pack_1',
                'method': 'GET'
            },
            # Pack management
            {
                'path': '/v1/packs/install',
                'method': 'POST',
                'payload': {'packs': 'libcloud'}
            },
            {
                'path': '/v1/packs/uninstall',
                'method': 'POST',
                'payload': {'packs': 'libcloud'}
            },
            {
                'path': '/v1/packs/register',
                'method': 'POST',
                'payload': {'types': ['actions']}
            },
            {
                'path': '/v1/packs/index/search',
                'method': 'POST',
                'payload': {'query': 'cloud'}
            },
            {
                'path': '/v1/packs/index/health',
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
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/config_schemas/dummy_pack_1',
                'method': 'GET'
            },
            {
                'path': '/v1/packs/views/file/dummy_pack_1/pack.yaml',
                'method': 'GET'
            },
            # Pack configs
            {
                'path': '/v1/configs',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/configs/dummy_pack_1',
                'method': 'GET'
            },
            {
                'path': '/v1/configs/dummy_pack_1',
                'method': 'PUT',
                'payload': {
                    'foo': 'bar'
                }
            },
            # Sensors
            {
                'path': '/v1/sensortypes',
                'method': 'GET',
                'is_getall': True
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
                'method': 'GET',
                'is_getall': True
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
                'method': 'GET',
                'is_getall': True
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
            {
                'path': '/v1/actionalias/match',
                'method': 'POST',
                'payload': {'command': 'test command string'}
            },
            # Rules
            {
                'path': '/v1/rules',
                'method': 'GET',
                'is_getall': True
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
                'payload': MOCK_RULE_1
            },
            {
                'path': '/v1/rules/%s' % (rule_model.ref),
                'method': 'DELETE'
            },
            # Rule enforcements
            {
                'path': '/v1/ruleenforcements',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/ruleenforcements/%s' % (enforcement_model.id),
                'method': 'GET'
            },
            # Action Executions
            {
                'path': '/v1/executions',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/executions/%s' % (execution_model.id),
                'method': 'GET'
            },
            {
                'path': '/v1/executions/%s/output' % (execution_model.id),
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
            },
            # Webhook
            {
                'path': '/v1/webhooks/st2',
                'method': 'POST',
                'payload': {
                    'trigger': 'some',
                    'payload': {
                        'some': 'thing'
                    }
                }
            },
            # Traces
            {
                'path': '/v1/traces',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/traces/%s' % (trace_model.id),
                'method': 'GET'
            },
            # Timers
            {
                'path': '/v1/timers',
                'method': 'GET'
            },
            {
                'path': '/v1/timers/%s' % (timer_model.id),
                'method': 'GET'
            },
            # Webhooks
            {
                'path': '/v1/webhooks',
                'method': 'GET'
            },
            {
                'path': '/v1/webhooks/git',
                'method': 'GET'
            },
            # RBAC - roles
            {
                'path': '/v1/rbac/roles',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/rbac/roles/admin',
                'method': 'GET'
            },
            # RBAC - user role assignments
            {
                'path': '/v1/rbac/role_assignments',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/rbac/role_assignments/%s' % (self.role_assignment_db_model['id']),
                'method': 'GET'
            },
            # RBAC - permission types
            {
                'path': '/v1/rbac/permission_types',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/rbac/permission_types/action',
                'method': 'GET'
            },
            # Action views
            {
                'path': '/v1/actions/views/overview',
                'method': 'GET',
                'is_getall': True
            },
            # Rule views
            {
                'path': '/v1/rules/views',
                'method': 'GET',
                'is_getall': True
            },
            # Service registry
            {
                'path': '/v1/service_registry/groups',
                'method': 'GET',
                'is_getall': True
            },
            {
                'path': '/v1/service_registry/groups/mock_service/members',
                'method': 'GET',
                'is_getall': True
            }
        ]

        self.use_user(self.users['no_permissions'])
        for endpoint in supported_endpoints:
            response = self._perform_request_for_endpoint(endpoint=endpoint)
            msg = '%s "%s" didn\'t return 403 status code (body=%s)' % (endpoint['method'],
                                                                        endpoint['path'],
                                                                        response.body)
            self.assertEqual(response.status_code, http_client.FORBIDDEN, msg)

        # Also test ?limit=-1 - non-admin user
        self.use_user(self.users['observer'])

        for endpoint in supported_endpoints:
            if not endpoint.get('is_getall', False):
                continue

            response = self.app.get(endpoint['path'] + '?limit=-1', expect_errors=True)
            msg = '%s "%s" didn\'t return 403 status code (body=%s)' % (endpoint['method'],
                                                                        endpoint['path'],
                                                                        response.body)
            self.assertEqual(response.status_code, http_client.FORBIDDEN, msg)

        # Also test ?limit=-1 - admin user
        self.use_user(self.users['admin'])

        for endpoint in supported_endpoints:
            if not endpoint.get('is_getall', False):
                continue

            response = self.app.get(endpoint['path'] + '?limit=-1')
            self.assertEqual(response.status_code, http_client.OK)

    def test_icon_png_file_is_whitelisted(self):
        self.use_user(self.users['no_permissions'])

        # Test that access to icon.png file doesn't require any permissions
        response = self.app.get('/v1/packs/views/file/dummy_pack_2/icon.png')
        self.assertEqual(response.status_code, http_client.OK)

        # Other files should return forbidden
        response = self.app.get('/v1/packs/views/file/dummy_pack_2/pack.yaml',
                                expect_errors=True)
        self.assertEqual(response.status_code, http_client.FORBIDDEN)

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
