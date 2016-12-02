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

import mock

from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.db.pack import PackDB
from st2common.persistence.pack import Pack
from st2common.services import packs as pack_service
from st2api.controllers.v1.actionexecutions import ActionExecutionsControllerMixin
from tests import FunctionalTest

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


class PacksControllerTestCase(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(PacksControllerTestCase, cls).setUpClass()

        cls.pack_db_1 = PackDB(name='pack1', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack1')
        cls.pack_db_2 = PackDB(name='pack2', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack2')
        Pack.add_or_update(cls.pack_db_1)
        Pack.add_or_update(cls.pack_db_2)

    def test_get_all(self):
        resp = self.app.get('/v1/packs')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/v1/actionalias did not return all aliases.')

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

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/packs/doesntexistfoo', expect_errors=True)
        self.assertEqual(resp.status_int, 404)

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_install(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = ActionExecutionAPI(id='123')
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_install_with_force_parameter(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = ActionExecutionAPI(id='123')
        payload = {'packs': ['some'], 'force': True}

        resp = self.app.post_json('/v1/packs/install', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(ActionExecutionsControllerMixin, '_handle_schedule_execution')
    def test_uninstall(self, _handle_schedule_execution):
        _handle_schedule_execution.return_value = ActionExecutionAPI(id='123')
        payload = {'packs': ['some']}

        resp = self.app.post_json('/v1/packs/uninstall', payload)

        self.assertEqual(resp.status_int, 202)
        self.assertEqual(resp.json, {'execution_id': '123'})

    @mock.patch.object(pack_service, 'fetch_pack_index',
                       mock.MagicMock(return_value=(PACK_INDEX, {})))
    def test_search(self):
        resp = self.app.post_json('/v1/packs/index/search', {'query': 'test'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test'], PACK_INDEX['test2']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'stanley'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test2']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'special'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test2']])

        # Search should be case insensitive by default
        resp = self.app.post_json('/v1/packs/index/search', {'query': 'TEST'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test'], PACK_INDEX['test2']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'SPECIAL'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test2']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'sPeCiAL'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test2']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'st2-dev'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': 'ST2-dev'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test']])

        resp = self.app.post_json('/v1/packs/index/search', {'query': '-dev'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, [PACK_INDEX['test']])

    @mock.patch.object(pack_service, 'fetch_pack_index',
                       mock.MagicMock(return_value=(PACK_INDEX, {})))
    def test_show(self):
        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'test'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, PACK_INDEX['test'])

        resp = self.app.post_json('/v1/packs/index/search', {'pack': 'test2'})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, PACK_INDEX['test2'])

    def test_packs_register_endpoint(self):
        # Register resources from all packs - make sure the count values are correctly added
        # together
        resp = self.app.post_json('/v1/packs/register')

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
        self.assertTrue(resp.json['configs'] >= 3)

        # Register resources from a specific pack
        resp = self.app.post_json('/v1/packs/register', {'packs': ['dummy_pack_1']})

        self.assertEqual(resp.status_int, 200)
        self.assertTrue(resp.json['actions'] >= 1)
        self.assertTrue(resp.json['sensors'] >= 1)
        self.assertTrue(resp.json['configs'] >= 1)

        # Register specific type for all packs
        resp = self.app.post_json('/v1/packs/register', {'types': ['sensor']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'sensors': 1})

        # Verify that plural name form also works
        resp = self.app.post_json('/v1/packs/register', {'types': ['sensors']})

        self.assertEqual(resp.status_int, 200)

        # Register specific type for a single packs
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1'], 'types': ['action']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 13})

        # Verify that plural name form also works
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1'], 'types': ['actions']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 13})

        # Register single resource from a single pack specified multiple times - verify that
        # resources from the same pack are only registered once
        resp = self.app.post_json('/v1/packs/register',
                                  {'packs': ['dummy_pack_1', 'dummy_pack_1', 'dummy_pack_1'],
                                   'types': ['actions']})

        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json, {'actions': 1, 'runners': 13})

        # Register resources from a single (non-existent pack)
        resp = self.app.post_json('/v1/packs/register', {'packs': ['doesntexist']},
                                  expect_errors=True)

        self.assertEqual(resp.status_int, 400)
        self.assertTrue('Pack "doesntexist" not found on disk:' in resp.json['faultstring'])
