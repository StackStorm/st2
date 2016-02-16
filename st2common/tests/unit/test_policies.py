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

import jsonschema

import st2tests
import st2common
from st2common.bootstrap.policiesregistrar import PolicyRegistrar
from st2common.bootstrap.policiesregistrar import register_policy_types, register_policies
from st2common.persistence.policy import PolicyType, Policy
from st2common.policies import ResourcePolicyApplicator, get_driver
from st2tests import DbTestCase, fixturesloader
from st2tests.fixturesloader import FixturesLoader
from st2tests.fixturesloader import get_fixtures_base_path

PACK = 'generic'
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


class PolicyTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(PolicyTest, cls).setUpClass()

        loader = FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK,
                                   fixtures_dict=TEST_FIXTURES)

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

    @classmethod
    def setUpClass(cls):
        super(PolicyBootstrapTest, cls).setUpClass()

        # Register common policy types
        register_policy_types(st2common)

    def test_register_policy_types(self):
        self.assertEqual(register_policy_types(st2tests), 2)

        type1 = PolicyType.get_by_ref('action.concurrency')
        self.assertEqual(type1.name, 'concurrency')
        self.assertEqual(type1.resource_type, 'action')

        type2 = PolicyType.get_by_ref('action.mock_policy_error')
        self.assertEqual(type2.name, 'mock_policy_error')
        self.assertEqual(type2.resource_type, 'action')

    def test_register_policies(self):
        # Note: Only one policy should be registered since second one fails validation
        pack_dir = os.path.join(fixturesloader.get_fixtures_base_path(), 'dummy_pack_1')
        self.assertEqual(register_policies(pack_dir=pack_dir), 1)

        p1 = Policy.get_by_ref('dummy_pack_1.test_policy_1')
        self.assertEqual(p1.name, 'test_policy_1')
        self.assertEqual(p1.pack, 'dummy_pack_1')
        self.assertEqual(p1.resource_ref, 'dummy_pack_1.local')
        self.assertEqual(p1.policy_type, 'action.concurrency')

        p2 = Policy.get_by_ref('dummy_pack_1.test_policy_2')
        self.assertEqual(p2, None)

    def test_register_policy_invalid_policy_type_references(self):
        # Policy references an invalid (inexistent) policy type
        registrar = PolicyRegistrar()
        policy_path = os.path.join(get_fixtures_base_path(),
                                   'dummy_pack_1/policies/policy_2.yaml')

        expected_msg = 'Referenced policy_type "action.mock_policy_error" doesnt exist'
        self.assertRaisesRegexp(ValueError, expected_msg, registrar._register_policy,
                                pack='dummy_pack_1', policy=policy_path)

    def test_make_sure_policy_parameters_are_validated_during_register(self):
        # Policy where specified parameters fail schema validation
        registrar = PolicyRegistrar()
        policy_path = os.path.join(get_fixtures_base_path(),
                                   'dummy_pack_1/policies/policy_3.yaml')

        expected_msg = '100 is greater than the maximum of 5'
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg,
                                registrar._register_policy, pack='dummy_pack_1',
                                policy=policy_path)
