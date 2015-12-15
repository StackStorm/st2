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

import mock

from st2common.transport.publishers import PoolPublisher
from st2reactor.rules.tester import RuleTester
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

FIXTURES_PACK = 'generic'

TEST_MODELS_TRIGGERS = {
    'triggertypes': ['triggertype1.yaml', 'triggertype2.yaml'],
    'triggers': ['trigger1.yaml', 'trigger2.yaml'],
    'triggerinstances': ['trigger_instance_1.yaml', 'trigger_instance_2.yaml']
}

TEST_MODELS_RULES = {
    'rules': ['rule1.yaml']
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class RuleTesterTestCase(CleanDbTestCase):
    def test_matching_trigger_from_file(self):
        rule_file_path = os.path.join(BASE_PATH, '../fixtures/rule.yaml')
        trigger_instance_file_path = os.path.join(BASE_PATH, '../fixtures/trigger_instance_1.yaml')
        tester = RuleTester(rule_file_path=rule_file_path,
                            trigger_instance_file_path=trigger_instance_file_path)
        matching = tester.evaluate()
        self.assertTrue(matching)

    def test_non_matching_trigger_from_file(self):
        rule_file_path = os.path.join(BASE_PATH, '../fixtures/rule.yaml')
        trigger_instance_file_path = os.path.join(BASE_PATH, '../fixtures/trigger_instance_2.yaml')
        tester = RuleTester(rule_file_path=rule_file_path,
                            trigger_instance_file_path=trigger_instance_file_path)
        matching = tester.evaluate()
        self.assertFalse(matching)

    def test_matching_trigger_from_db(self):
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS_TRIGGERS)
        trigger_instance_db = models['triggerinstances']['trigger_instance_2.yaml']
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS_RULES)
        rule_db = models['rules']['rule1.yaml']
        tester = RuleTester(rule_ref=rule_db.ref,
                            trigger_instance_id=str(trigger_instance_db.id))
        matching = tester.evaluate()
        self.assertTrue(matching)

    def test_non_matching_trigger_from_db(self):
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS_TRIGGERS)
        trigger_instance_db = models['triggerinstances']['trigger_instance_1.yaml']
        models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                      fixtures_dict=TEST_MODELS_RULES)
        rule_db = models['rules']['rule1.yaml']
        tester = RuleTester(rule_ref=rule_db.ref,
                            trigger_instance_id=str(trigger_instance_db.id))
        matching = tester.evaluate()
        self.assertFalse(matching)
