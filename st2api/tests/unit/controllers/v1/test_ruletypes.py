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

import st2common.bootstrap.ruletypesregistrar as ruletypes_registrar
from st2tests.api import FunctionalTest


class TestRuleTypesController(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(TestRuleTypesController, cls).setUpClass()

        # Register rule types fixtures
        ruletypes_registrar.register_rule_types()

    def test_get_one(self):
        list_resp = self.app.get('/v1/ruletypes')
        self.assertEqual(list_resp.status_int, 200)
        self.assertTrue(len(list_resp.json) > 0, '/v1/ruletypes did not return correct ruletypes.')
        ruletype_id = list_resp.json[0]['id']
        get_resp = self.app.get('/v1/ruletypes/%s' % ruletype_id)
        retrieved_id = get_resp.json['id']
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(retrieved_id, ruletype_id, '/v1/ruletypes returned incorrect ruletype.')

    def test_get_all(self):
        resp = self.app.get('/v1/ruletypes')
        self.assertEqual(resp.status_int, 200)
        self.assertTrue(len(resp.json) > 0, '/v1/ruletypes did not return correct ruletypes.')

    def test_get_one_fail_doesnt_exist(self):
        resp = self.app.get('/v1/ruletypes/1', expect_errors=True)
        self.assertEqual(resp.status_int, 404)
