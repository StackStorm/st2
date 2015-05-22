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

from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.persistence.policy import PolicyType, Policy
from st2tests.fixturesloader import FixturesLoader
from st2tests import DbTestCase


TEST_FIXTURES = {
    'policytypes': [
        'policy_type_1.yaml',
        'policy_type_2.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_2.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


class PolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(PolicyTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            Policy.add_or_update(PolicyAPI.to_model(instance))

    def test_get_by_ref(self):
        policy_db = Policy.get_by_ref('core.local.concurrency')
        self.assertIsNotNone(policy_db)
        self.assertEqual(policy_db.pack, 'core')
        self.assertEqual(policy_db.name, 'local.concurrency')

        policy_type_db = PolicyType.get_by_ref(policy_db.policy_type)
        self.assertIsNotNone(policy_type_db)
        self.assertEqual(policy_type_db.resource_type, 'action')
        self.assertEqual(policy_type_db.name, 'concurrency')
