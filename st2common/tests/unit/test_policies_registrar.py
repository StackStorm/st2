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

import st2common
from st2common.bootstrap.policiesregistrar import register_policy_types
import st2common.bootstrap.policiesregistrar as policies_registrar
from st2common.persistence.policy import Policy
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
