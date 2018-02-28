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

from st2common.models.api.rule import RuleAPI
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.rule import Rule
from st2common.persistence.trigger import Trigger
from st2common.persistence.keyvalue import KeyValuePair
from st2tests import fixturesloader
from st2tests import base

from st2tests import config as tests_config
tests_config.parse_args()

FIXTURES_PACK = 'generic'

TEST_FIXTURES = {
    'rules': ['rule_jinja_trigger_params.yaml'],
}


class RuleAPIModelTests(base.CleanDbTestCase):
    def __init__(self, *args, **kwargs):
        super(RuleAPIModelTests, self).__init__(*args, **kwargs)
        self.models = None
        self.loader = fixturesloader.FixturesLoader()

    def setUp(self):
        super(RuleAPIModelTests, self).setUp()

    def test_jinja_resolve_trigger_params(self):
        kv_db = KeyValuePairDB(scope='st2kv.system', name='foo', value='foo', secret=False)
        KeyValuePair.add_or_update(kv_db)
        kv_db = KeyValuePairDB(scope='st2kv.system', name='bar', value='bar', secret=False)
        KeyValuePair.add_or_update(kv_db)
        all_fixtures = self.loader.load_fixtures(fixtures_pack=FIXTURES_PACK,
                                                 fixtures_dict=TEST_FIXTURES)
        rule_dict = all_fixtures['rules']['rule_jinja_trigger_params.yaml']
        rule_api = RuleAPI(**rule_dict)
        rule_db = RuleAPI.to_model(rule_api)
        rule_db = Rule.add_or_update(rule_db)
        trigger_db = Trigger.get_by_ref(rule_db.trigger)
        self.assertEqual(trigger_db.parameters['x'], 'foo')
        self.assertEqual(trigger_db.parameters['y'], 'bar')
