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
import six

import st2tests

from st2common.content.policies import register_policy_types, register_policies
from st2common.models.api.action import ActionAPI, RunnerTypeAPI
from st2common.models.api.policy import PolicyTypeAPI, PolicyAPI
from st2common.persistence.action import Action
from st2common.persistence.policy import PolicyType, Policy
from st2common.persistence.runner import RunnerType
from st2common.policies import ResourcePolicyApplicator, get_driver
from st2tests import DbTestCase, fixturesloader


TEST_FIXTURES = {
    'runners': [
        'testrunner1.yaml'
    ],
    'actions': [
        'action1.yaml'
    ],
    'policytypes': [
        'fake_policy_type_1.yaml',
        'fake_policy_type_2.yaml'
    ],
    'policies': [
        'policy_1.yaml',
        'policy_2.yaml'
    ]
}

PACK = 'generic'
LOADER = fixturesloader.FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


class PolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(PolicyTest, cls).setUpClass()

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            Action.add_or_update(ActionAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policytypes']):
            instance = PolicyTypeAPI(**fixture)
            PolicyType.add_or_update(PolicyTypeAPI.to_model(instance))

        for _, fixture in six.iteritems(FIXTURES['policies']):
            instance = PolicyAPI(**fixture)
            Policy.add_or_update(PolicyAPI.to_model(instance))

    def test_get_by_ref(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency')
        self.assertIsNotNone(policy_db)
        self.assertEqual(policy_db.pack, 'wolfpack')
        self.assertEqual(policy_db.name, 'action-1.concurrency')

        policy_type_db = PolicyType.get_by_ref(policy_db.policy_type)
        self.assertIsNotNone(policy_type_db)
        self.assertEqual(policy_type_db.resource_type, 'action')
        self.assertEqual(policy_type_db.name, 'concurrency')

    def test_get_driver(self):
        policy_db = Policy.get_by_ref('wolfpack.action-1.concurrency')
        policy = get_driver(policy_db.ref, policy_db.policy_type, **policy_db.parameters)
        self.assertIsInstance(policy, ResourcePolicyApplicator)
        self.assertEqual(policy._policy_ref, policy_db.ref)
        self.assertEqual(policy._policy_type, policy_db.policy_type)
        self.assertTrue(hasattr(policy, 'threshold'))
        self.assertEqual(policy.threshold, 3)


class PolicyBootstrapTest(DbTestCase):

    def test_register_policy_types(self):
        self.assertEqual(register_policy_types(st2tests), 2)

        type1 = PolicyType.get_by_ref('action.concurrency')
        self.assertEqual(type1.name, 'concurrency')
        self.assertEqual(type1.resource_type, 'action')

        type2 = PolicyType.get_by_ref('action.mock_policy_error')
        self.assertEqual(type2.name, 'mock_policy_error')
        self.assertEqual(type2.resource_type, 'action')

    def test_register_policies(self):
        pack_dir = os.path.join(fixturesloader.get_fixtures_base_path(), 'dummy_pack_1')
        self.assertEqual(register_policies(pack_dir=pack_dir), 2)

        p1 = Policy.get_by_ref('dummy_pack_1.test_policy_1')
        self.assertEqual(p1.name, 'test_policy_1')
        self.assertEqual(p1.pack, 'dummy_pack_1')
        self.assertEqual(p1.resource_ref, 'dummy_pack_1.local')
        self.assertEqual(p1.policy_type, 'action.concurrency')

        p2 = Policy.get_by_ref('dummy_pack_1.test_policy_2')
        self.assertEqual(p2.name, 'test_policy_2')
        self.assertEqual(p2.pack, 'dummy_pack_1')
        self.assertEqual(p2.resource_ref, 'dummy_pack_1.local')
        self.assertEqual(p2.policy_type, 'action.mock_policy_error')
        self.assertEqual(p2.resource_ref, 'dummy_pack_1.local')
