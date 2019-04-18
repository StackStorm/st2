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

from st2api.controllers.v1.rule_enforcements import RuleEnforcementController
from st2tests.fixturesloader import FixturesLoader

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

http_client = six.moves.http_client

TEST_FIXTURES = {
    'enforcements': ['enforcement1.yaml', 'enforcement2.yaml', 'enforcement3.yaml']
}

FIXTURES_PACK = 'rule_enforcements'


class RuleEnforcementControllerTestCase(FunctionalTest,
        APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/ruleenforcements'
    controller_cls = RuleEnforcementController
    include_attribute_field_name = 'enforced_at'
    exclude_attribute_field_name = 'status'

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(RuleEnforcementControllerTestCase, cls).setUpClass()
        cls.models = RuleEnforcementControllerTestCase.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        RuleEnforcementControllerTestCase.ENFORCEMENT_1 = \
            cls.models['enforcements']['enforcement1.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/ruleenforcements')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)

    def test_get_all_minus_one(self):
        resp = self.app.get('/v1/ruleenforcements/?limit=-1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 3)

    def test_get_all_limit(self):
        resp = self.app.get('/v1/ruleenforcements/?limit=1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_get_all_limit_negative_number(self):
        resp = self.app.get('/v1/ruleenforcements?limit=-22', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

    def test_get_one_by_id(self):
        e_id = str(RuleEnforcementControllerTestCase.ENFORCEMENT_1.id)
        resp = self.app.get('/v1/ruleenforcements/%s' % e_id)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(resp.json['id'], e_id)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/ruleenforcements/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_filter_by_rule_ref(self):
        resp = self.app.get('/v1/ruleenforcements?rule_ref=wolfpack.golden_rule')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_rule_id(self):
        resp = self.app.get('/v1/ruleenforcements?rule_id=565e15c032ed35086c54f331')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

    def test_filter_by_execution_id(self):
        resp = self.app.get('/v1/ruleenforcements?execution=565e15cd32ed350857dfa620')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_trigger_instance_id(self):
        resp = self.app.get('/v1/ruleenforcements?trigger_instance=565e15ce32ed350857dfa623')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def test_filter_by_enforced_at(self):
        resp = self.app.get('/v1/ruleenforcements?enforced_at_gt=2015-12-01T21:49:01.000000Z')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/v1/ruleenforcements?enforced_at_lt=2015-12-01T21:49:01.000000Z')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)

    def _insert_mock_models(self):
        enfrocement_ids = [enforcement['id'] for enforcement in
                           self.models['enforcements'].values()]
        return enfrocement_ids

    def _delete_mock_models(self, object_ids):
        pass
