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
    'PackConfigSchemaControllerTestCase'
]


class PackConfigSchemaControllerTestCase(FunctionalTest):
    register_packs = True

    def test_get_all(self):
        resp = self.app.get('/v1/config_schema')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1, '/v1/config_schema did not return all schemas.')

    def test_get_one(self):
        resp = self.app.get('/v1/config_schema/dummy_pack_1')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['pack'], 'dummy_pack_1')
        self.assertTrue('api_key' in resp.json['attributes'])
