# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import copy
import glob
import mock

from st2tests.api import FunctionalTest
from st2api.controllers.v1.pack_configs import PackConfigsController
from st2tests.fixturesloader import get_fixtures_packs_base_path

__all__ = [
    'PackConfigsControllerTestCase'
]

PACKS_PATH = get_fixtures_packs_base_path()
CONFIGS_COUNT = len(glob.glob('%s/configs/*.yaml' % (PACKS_PATH)))
assert CONFIGS_COUNT > 1


class PackConfigsControllerTestCase(FunctionalTest):
    register_packs = True
    register_pack_configs = True

    def test_get_all(self):
        resp = self.app.get('/v1/configs')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), CONFIGS_COUNT, '/v1/configs did not return all configs.')

    def test_get_one_success(self):
        resp = self.app.get('/v1/configs/dummy_pack_1', params={'show_secrets': True},
                            expect_errors=True)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['pack'], 'dummy_pack_1')
        self.assertEqual(resp.json['values']['api_key'], '{{st2kv.user.api_key}}')
        self.assertEqual(resp.json['values']['region'], 'us-west-1')

    def test_get_one_mask_secret(self):
        resp = self.app.get('/v1/configs/dummy_pack_1')
        self.assertEqual(resp.status_int, 200)
        self.assertNotEqual(resp.json['values']['api_key'], '{{st2kv.user.api_key}}')

    def test_get_one_pack_config_doesnt_exist(self):
        # Pack exists, config doesnt
        resp = self.app.get('/v1/configs/dummy_pack_2',
                            expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertTrue('Unable to identify resource with pack_ref ' in resp.json['faultstring'])

        # Pack doesn't exist
        resp = self.app.get('/v1/configs/pack_doesnt_exist',
                            expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        # Changed from : 'Unable to find the PackDB instance.'
        self.assertTrue('Unable to identify resource with pack_ref' in resp.json['faultstring'])

    @mock.patch.object(PackConfigsController, '_dump_config_to_disk', mock.MagicMock())
    def test_put_pack_config(self):
        get_resp = self.app.get('/v1/configs/dummy_pack_1', params={'show_secrets': True},
                                expect_errors=True)
        config = copy.copy(get_resp.json['values'])
        config['region'] = 'us-west-2'

        put_resp = self.app.put_json('/v1/configs/dummy_pack_1', config)
        self.assertEqual(put_resp.status_int, 200)
        put_resp_undo = self.app.put_json('/v1/configs/dummy_pack_1?show_secrets=true',
                                          get_resp.json['values'], expect_errors=True)
        self.assertEqual(put_resp.status_int, 200)
        self.assertEqual(get_resp.json, put_resp_undo.json)

    @mock.patch.object(PackConfigsController, '_dump_config_to_disk', mock.MagicMock())
    def test_put_invalid_pack_config(self):
        get_resp = self.app.get('/v1/configs/dummy_pack_11', params={'show_secrets': True},
                                expect_errors=True)
        config = copy.copy(get_resp.json['values'])
        put_resp = self.app.put_json('/v1/configs/dummy_pack_11', config, expect_errors=True)
        self.assertEqual(put_resp.status_int, 400)
        expected_msg = ('Values specified as "secret: True" in config schema are automatically '
                        'decrypted by default. Use of "decrypt_kv" jinja filter is not allowed '
                        'for such values. Please check the specified values in the config or '
                        'the default values in the schema.')
        self.assertTrue(expected_msg in put_resp.json['faultstring'])
