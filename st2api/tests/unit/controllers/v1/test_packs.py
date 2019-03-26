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

import requests
import mock

from st2common.content.loader import ContentPackLoader
from st2common.models.db.pack import PackDB
from st2common.persistence.pack import Pack
from st2common.persistence.action import Action
from st2common.router import Response
from st2common.services import packs as pack_service
from st2api.controllers.v1.actionexecutions import ActionExecutionsControllerMixin
from st2api.controllers.v1.packs import PacksController
from st2api.controllers.v1.packs import ENTITIES

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

from st2tests.fixturesloader import get_fixtures_base_path

__all__ = [
    'PacksControllerTestCase'
]

PACK_INDEX = {
    "test": {
        "version": "0.4.0",
        "name": "test",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test",
        "author": "st2-dev",
        "keywords": ["some", "search", "another", "terms"],
        "email": "info@stackstorm.com",
        "description": "st2 pack to test package management pipeline"
    },
    "test2": {
        "version": "0.5.0",
        "name": "test2",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test2",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline"
    }
}

PACK_INDEXES = {
    'http://main.example.com': PACK_INDEX,
    'http://fallback.example.com': {
        "test": {
            "version": "0.1.0",
            "name": "test",
            "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test",
            "author": "st2-dev",
            "keywords": ["some", "search", "another", "terms"],
            "email": "info@stackstorm.com",
            "description": "st2 pack to test package management pipeline"
        }
    },
    'http://override.example.com': {
        "test2": {
            "version": "1.0.0",
            "name": "test2",
            "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test2",
            "author": "stanley",
            "keywords": ["some", "special", "terms"],
            "email": "info@stackstorm.com",
            "description": "another st2 pack to test package management pipeline"
        }
    },
    'http://broken.example.com': requests.exceptions.RequestException('index is broken')
}


def mock_index_get(url, *args, **kwargs):
    index = PACK_INDEXES[url]

    if isinstance(index, requests.exceptions.RequestException):
        raise index

    status = 200
    content = {
        'metadata': {},
        'packs': index
    }

    # Return mock response object

    mock_resp = mock.Mock()
    mock_resp.raise_for_status = mock.Mock()
    mock_resp.status_code = status
    mock_resp.content = content
    mock_resp.json = mock.Mock(
        return_value=content
    )
    return mock_resp


class PacksControllerTestCase(FunctionalTest,
                              APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/packs'
    controller_cls = PacksController
    include_attribute_field_name = 'version'
    exclude_attribute_field_name = 'author'

    @classmethod
    def setUpClass(cls):
        super(PacksControllerTestCase, cls).setUpClass()

        cls.pack_db_1 = PackDB(name='pack1', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack1')
        cls.pack_db_2 = PackDB(name='pack2', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack2')
        cls.pack_db_3 = PackDB(name='pack3-name', ref='pack3-ref', description='foo',
                               version='0.1.0', author='foo',
                               email='test@example.com')
        Pack.add_or_update(cls.pack_db_1)
        Pack.add_or_update(cls.pack_db_2)
        Pack.add_or_update(cls.pack_db_3)

    def test_get_all(self):
        resp = self.app.get('/v1/packs')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3, '/v1/actionalias did not return all packs.')

    def test_get_one(self):
        # Get by id
        resp = self.app.get('/v1/packs/%s' % (self.pack_db_1.id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['name'], self.pack_db_1.name)

        # Get by name
        resp = self.app.get('/v1/packs/%s' % (self.pack_db_1.ref))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['ref'], self.pack_db_1.ref)
        self.assertEqual(resp.json['name'], self.pack_db_1.name)

        # Get by ref (ref != name)
        resp = self.app.get('/v1/packs/%s' % (self.pack_db_3.ref))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['ref'], self.pack_db_3.ref)

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/packs/doesntexistfoo', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_install(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = Response(json={'id': '123'})
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_install_with_force_parameter(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = Response(json={'id': '123'})
        payload = {'packs': ['some'], 'force': True}

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_uninstall(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = Response(json={'id': '123'})
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/uninstall', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(pack_service, 'fetch_pack_index',
                       mock.MagicMock(return_value=(PACK_INDEX, {})))
    def test_search_with_query(self):
        test_scenarios = [
            {
                'input': {'query': 'test'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test'], PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'stanley'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'special'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'TEST'},  # Search should be case insensitive by default
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test'], PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'SPECIAL'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'sPeCiAL'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test2']]
            },
            {
                'input': {'query': 'st2-dev'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test']]
            },
            {
                'input': {'query': 'ST2-dev'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test']]
            },
            {
                'input': {'query': '-dev'},
                'expected_code': 200,
                'expected_result': [PACK_INDEX['test']]
            },
            {
                'input': {'query': 'core'},
                'expected_code': 200,
                'expected_result': []
            }
        ]

        for scenario in test_scenarios:
            resp = self.app.post_json('/v1/packs/index/search', scenario['input'])
            self.assertEqual(resp.status_int, scenario['expected_code'])
            self.assertEqual(resp.json, scenario['expected_result'])

    @mock.patch.object(pack_service, 'get_pack_from_index',
                       mock.MagicMock(return_value=PACK_INDEX['test']))
    def test_search_with_pack_has_result(self):
        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'st2-dev'})
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, PACK_INDEX['test'])

    @mock.patch.object(pack_service, 'get_pack_from_index',
                       mock.MagicMock(return_value=None))
    def test_search_with_pack_no_result(self):
        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'not-found'})
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [])

    @mock.patch.object(pack_service, 'fetch_pack_index',
                       mock.MagicMock(return_value=(PACK_INDEX, {})))
    def test_show(self):
        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'test'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, PACK_INDEX['test'])

        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'test2'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, PACK_INDEX['test2'])

    @mock.patch.object(pack_service, '_build_index_list',
                       mock.MagicMock(return_value=['http://main.example.com']))
    @mock.patch.object(requests, 'get', mock_index_get)
    def test_index_health(self):
        resp = self.app.get('/v1/packs/index/health')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'packs': {
                'count': 2
            },
            'indexes': {
                'count': 1,
                'status': [{
                    'url': 'http://main.example.com',
                    'message': 'Success.',
                    'packs': 2,
                    'error': None
                }],
                'valid': 1,
                'errors': {},
                'invalid': 0
            }
        })

    @mock.patch.object(pack_service, '_build_index_list',
                       mock.MagicMock(return_value=['http://main.example.com',
                                                    'http://broken.example.com']))
    @mock.patch.object(requests, 'get', mock_index_get)
    def test_index_health_broken(self):
        resp = self.app.get('/v1/packs/index/health')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'packs': {
                'count': 2
            },
            'indexes': {
                'count': 2,
                'status': [{
                    'url': 'http://main.example.com',
                    'message': 'Success.',
                    'packs': 2,
                    'error': None
                }, {
                    'url': 'http://broken.example.com',
                    'message': "RequestException('index is broken',)",
                    'packs': 0,
                    'error': 'unresponsive'
                }],
                'valid': 1,
                'errors': {
                    'unresponsive': 1
                },
                'invalid': 1
            }
        })

    @mock.patch.object(pack_service, '_build_index_list',
                       mock.MagicMock(return_value=['http://main.example.com']))
    @mock.patch.object(requests, 'get', mock_index_get)
    def test_index(self):
        resp = self.app.get('/v1/packs/index')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'status': [{
                'url': 'http://main.example.com',
                'message': 'Success.',
                'packs': 2,
                'error': None
            }],
            'index': PACK_INDEX
        })

    @mock.patch.object(pack_service, '_build_index_list',
                       mock.MagicMock(return_value=['http://fallback.example.com',
                                                    'http://main.example.com']))
    @mock.patch.object(requests, 'get', mock_index_get)
    def test_index_fallback(self):
        resp = self.app.get('/v1/packs/index')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'status': [{
                'url': 'http://fallback.example.com',
                'message': 'Success.',
                'packs': 1,
                'error': None
            }, {
                'url': 'http://main.example.com',
                'message': 'Success.',
                'packs': 2,
                'error': None
            }],
            'index': PACK_INDEX
        })

    @mock.patch.object(pack_service, '_build_index_list',
                       mock.MagicMock(return_value=['http://main.example.com',
                                                    'http://override.example.com']))
    @mock.patch.object(requests, 'get', mock_index_get)
    def test_index_override(self):
        resp = self.app.get('/v1/packs/index')

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {
            'status': [{
                'url': 'http://main.example.com',
                'message': 'Success.',
                'packs': 2,
                'error': None
            }, {
                'url': 'http://override.example.com',
                'message': 'Success.',
                'packs': 1,
                'error': None
            }],
            'index': {
                'test': PACK_INDEX['test'],
                'test2': PACK_INDEXES['http://override.example.com']['test2']
            }
        })

    def test_packs_register_endpoint_resource_register_order(self):
        # Verify that resources are registered in the same order as they are inside
        # st2-register-content.
        # Note: Sadly there is no easier / better way to test this
        resource_types = list(ENTITIES.keys())
        expected_order = [
            'trigger',
            'sensor',
            'action',
            'rule',
            'alias',
            'policy',
            'config'
        ]
        self.assertEqual(resource_types, expected_order)

    @mock.patch.object(ContentPackLoader, 'get_packs')
    def test_packs_register_endpoint(self, mock_get_packs):
        # Register resources from all packs - make sure the count values are correctly added
        # together

        # Note: We only register a couple of packs and not all on disk to speed
        # things up. Registering all the packs takes a long time.
        fixtures_base_path = get_fixtures_base_path()
        packs_base_path = os.path.join(fixtures_base_path, 'packs')
        pack_names = [
            'dummy_pack_1',
            'dummy_pack_2',
            'dummy_pack_3',
            'dummy_pack_10',
        ]
        mock_return_value = {}
        for pack_name in pack_names:
            mock_return_value[pack_name] = os.path.join(packs_base_path, pack_name)

        mock_get_packs.return_value = mock_return_value

        resp = self.app.post_json('/v1/packs/register', {'fail_on_failure': False})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue('runners' in resp.json)
        self.assertTrue('actions' in resp.json)
        self.assertTrue('triggers' in resp.json)
        self.assertTrue('sensors' in resp.json)
        self.assertTrue('rules' in resp.json)
        self.assertTrue('rule_types' in resp.json)
        self.assertTrue('aliases' in resp.json)
        self.assertTrue('policy_types' in resp.json)
        self.assertTrue('policies' in resp.json)
        self.assertTrue('configs' in resp.json)

        self.assertTrue(resp.json['actions'] >= 3)
        self.assertTrue(resp.json['configs'] >= 1)

        # Register resources from a specific pack
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1'],
                                                         'fail_on_failure': False})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(resp.json['actions'] >= 1)
        self.assertTrue(resp.json['sensors'] >= 1)
        self.assertTrue(resp.json['configs'] >= 1)

        # Verify metadata_file attribute is set
        action_dbs = Action.query(pack='dummy_pack_1')
        self.assertEqual(action_dbs[0].metadata_file, 'actions/my_action.yaml')

        # Register 'all' resource types should try include any possible content for the pack
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1'],
                                                         'fail_on_failure': False,
                                                         'types': ['all']})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue('runners' in resp.json)
        self.assertTrue('actions' in resp.json)
        self.assertTrue('triggers' in resp.json)
        self.assertTrue('sensors' in resp.json)
        self.assertTrue('rules' in resp.json)
        self.assertTrue('rule_types' in resp.json)
        self.assertTrue('aliases' in resp.json)
        self.assertTrue('policy_types' in resp.json)
        self.assertTrue('policies' in resp.json)
        self.assertTrue('configs' in resp.json)

        # Registering single resource type should also cause dependent resources
        # to be registered
        # * actions -> runners
        # * rules -> rule types
        # * policies -> policy types
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1'],
                                                         'fail_on_failure': False,
                                                         'types': ['actions']})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(resp.json['runners'] >= 1)
        self.assertTrue(resp.json['actions'] >= 1)

        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1'],
                                                         'fail_on_failure': False,
                                                         'types': ['rules']})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(resp.json['rule_types'] >= 1)
        self.assertTrue(resp.json['rules'] >= 1)

        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_2'],
                                                         'fail_on_failure': False,
                                                         'types': ['policies']})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(resp.json['policy_types'] >= 1)
        self.assertTrue(resp.json['policies'] >= 0)

        # Register specific type for all packs
        resp = self.app.post_json('/v1/packs/register', {'types': ['sensor'],
                                                         'fail_on_failure': False})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'sensors': 3})

        # Verify that plural name form also works
        resp = self.app.post_json('/v1/packs/register', {'types': ['sensors'],
                                                         'fail_on_failure': False})
        self.assertEqual(resp.status_int, 200)

        # Register specific type for a single packs
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1'], 'types': ['action']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 15})

        # Verify that plural name form also works
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1'], 'types': ['actions']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 15})

        # Register single resource from a single pack specified multiple times - verify that
        # resources from the same pack are only registered once
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1', 'dummy_pack_1', 'dummy_pack_1'],
                                   'types': ['actions'],
                                   'fail_on_failure': False})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 15})

        # Register resources from a single (non-existent pack)
        resp = self.app.post_json('/v1/packs/register', {'packs': ['doesntexist']},
                                  expect_errors=True)

        self.assertEqual(resp.status_int, 400)
        self.assertTrue('Pack "doesntexist" not found on disk:' in resp.json['faultstring'])

        # Fail on failure is enabled by default
        resp = self.app.post_json('/v1/packs/register', expect_errors=True)

        expected_msg = 'Failed to register pack "dummy_pack_10":'
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(expected_msg in resp.json['faultstring'])

        # Fail on failure (broken pack metadata)
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1']},
                                  expect_errors=True)

        expected_msg = 'Referenced policy_type "action.mock_policy_error" doesnt exist'
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(expected_msg in resp.json['faultstring'])

        # Fail on failure (broken action metadata)
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_15']},
                                  expect_errors=True)

        expected_msg = 'Failed to register action'
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(expected_msg in resp.json['faultstring'])

        expected_msg = '\'stringa\' is not valid under any of the given schemas'
        self.assertEqual(resp.status_int, 400)
        self.assertTrue(expected_msg in resp.json['faultstring'])

    def test_get_all_invalid_exclude_and_include_parameter(self):
        pass

    def _insert_mock_models(self):
        return [self.pack_db_1['id'], self.pack_db_2['id'], self.pack_db_3['id']]

    def _do_delete(self, object_ids):
        pass
