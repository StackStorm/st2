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

from tests import FunctionalTest

__all__ = [
    'PackConfigSchemasControllerTestCase'
]


class PackConfigSchemasControllerTestCase(FunctionalTest):
    register_packs = True

    def test_get_all(self):
        resp = self.app.get('/v1/config_schemas')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 4, '/v1/config_schemas did not return all schemas.')

    def test_get_one_success(self):
        resp = self.app.get('/v1/config_schemas/dummy_pack_1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['pack'], 'dummy_pack_1')
        self.assertTrue('api_key' in resp.json['attributes'])

    def test_get_one_doesnt_exist(self):
        # Pack exists, schema doesnt
        resp = self.app.get('/v1/config_schemas/dummy_pack_2',
                            expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertTrue('Unable to identify resource with pack_ref ' in resp.json['faultstring'])

        # Pack doesn't exist
        resp = self.app.get('/v1/config_schemas/pack_doesnt_exist',
                            expect_errors=True)
        self.assertEqual(resp.status_int, 404)
        self.assertTrue('Unable to find the PackDB instance' in resp.json['faultstring'])
