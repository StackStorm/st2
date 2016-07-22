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

import st2common
import st2tests
from st2common.bootstrap.policiesregistrar import PolicyRegistrar
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.bootstrap.policiesregistrar import register_policies
import st2common.bootstrap.policiesregistrar as policies_registrar
from st2common.persistence.policy import Policy
from st2common.persistence.policy import PolicyType
from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import get_fixtures_packs_base_path

__all__ = [
    'PoliciesRegistrarTestCase'
]


class PoliciesRegistrarTestCase(CleanDbTestCase):
    def setUp(self):
        super(PoliciesRegistrarTestCase, self).setUp()

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

    def test_register_all_policies(self):
        policies_dbs = Policy.get_all()
        self.assertEqual(len(policies_dbs), 0)

        packs_base_path = get_fixtures_packs_base_path()
        count = policies_registrar.register_policies(packs_base_paths=[packs_base_path])
        self.assertEqual(count, 2)

        # Verify PolicyDB objects have been created
        policies_dbs = Policy.get_all()
        self.assertEqual(len(policies_dbs), 2)

        self.assertEqual(policies_dbs[0].name, 'test_policy_1')
        self.assertEqual(policies_dbs[0].policy_type, 'action.concurrency')

        # Verify that a default value for parameter "action" which isn't provided in the file is set
        self.assertEqual(policies_dbs[0].parameters['action'], 'delay')
        self.assertEqual(policies_dbs[0].parameters['threshold'], 3)

    def test_register_policies_from_pack(self):
        pack_dir = os.path.join(get_fixtures_packs_base_path(), 'dummy_pack_1')
        self.assertEqual(register_policies(pack_dir=pack_dir), 2)

        p1 = Policy.get_by_ref('dummy_pack_1.test_policy_1')
        self.assertEqual(p1.name, 'test_policy_1')
        self.assertEqual(p1.pack, 'dummy_pack_1')
        self.assertEqual(p1.resource_ref, 'dummy_pack_1.local')
        self.assertEqual(p1.policy_type, 'action.concurrency')
        # Verify that a default value for parameter "action" which isn't provided in the file is set
        self.assertEqual(p1.parameters['action'], 'delay')

        p2 = Policy.get_by_ref('dummy_pack_1.test_policy_2')
        self.assertEqual(p2, None)

    def test_register_policy_invalid_policy_type_references(self):
        # Policy references an invalid (inexistent) policy type
        registrar = PolicyRegistrar()
        policy_path = os.path.join(get_fixtures_packs_base_path(),
                                   'dummy_pack_1/policies/policy_2.yaml')

        expected_msg = 'Referenced policy_type "action.mock_policy_error" doesnt exist'
        self.assertRaisesRegexp(ValueError, expected_msg, registrar._register_policy,
                                pack='dummy_pack_1', policy=policy_path)

    def test_make_sure_policy_parameters_are_validated_during_register(self):
        # Policy where specified parameters fail schema validation
        registrar = PolicyRegistrar()
        policy_path = os.path.join(get_fixtures_packs_base_path(),
                                   'dummy_pack_2/policies/policy_3.yaml')

        expected_msg = '100 is greater than the maximum of 5'
        self.assertRaisesRegexp(jsonschema.ValidationError, expected_msg,
                                registrar._register_policy, pack='dummy_pack_2',
                                policy=policy_path)
