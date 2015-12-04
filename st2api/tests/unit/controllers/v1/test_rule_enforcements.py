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

import six

from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

http_client = six.moves.http_client

TEST_FIXTURES = {
    'enforcements': ['enforcement1.yaml', 'enforcement2.yaml', 'enforcement3.yaml']
}

FIXTURES_PACK = 'rule_enforcements'


class TestRuleEnforcementController(FunctionalTest):

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(TestRuleEnforcementController, cls).setUpClass()
        models = TestRuleEnforcementController.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        TestRuleEnforcementController.ENFORCEMENT_1 = models['enforcements']['enforcement1.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/ruleenforcements')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)

    def test_get_one_by_id(self):
        e_id = str(TestRuleEnforcementController.ENFORCEMENT_1.id)
        resp = self.app.get('/v1/ruleenforcements/%s' % e_id)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json['id'], e_id)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/ruleenforcements/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_filter_by_rule_ref(self):
        resp = self.app.get('/v1/ruleenforcements/?rule_ref=wolfpack.golden_rule')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_rule_id(self):
        resp = self.app.get('/v1/ruleenforcements/?rule_id=565e15c032ed35086c54f331')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

    def test_filter_by_execution_id(self):
        resp = self.app.get('/v1/ruleenforcements/?execution=565e15cd32ed350857dfa620')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_trigger_instance_id(self):
        resp = self.app.get('/v1/ruleenforcements/?trigger_instance=565e15ce32ed350857dfa623')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_enforced_at(self):
        resp = self.app.get('/v1/ruleenforcements/?enforced_at_gt=2015-12-01T21:49:01.000000Z')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/v1/ruleenforcements/?enforced_at_lt=2015-12-01T21:49:01.000000Z')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)
