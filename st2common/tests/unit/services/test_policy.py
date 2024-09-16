# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

# This import must be early for import-time side-effects.
import st2tests

import st2common

from st2common.bootstrap import policiesregistrar as policies_registrar
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2common.constants import action as action_constants
from st2common.constants import policy as policy_constants
from st2common.models.db import action as action_db_models
from st2common.services import action as action_service
from st2common.services import policies as policy_service

from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests import fixturesloader as fixtures


TEST_FIXTURES = {
    "actions": [
        "action1.yaml",  # wolfpack.action-1
        "action2.yaml",  # wolfpack.action-2
        "local.yaml",  # core.local
    ],
    "policies": [
        "policy_2.yaml",  # mock policy on wolfpack.action-1
        "policy_5.yaml",  # concurrency policy on wolfpack.action-2
    ],
}


class PolicyServiceTestCase(st2tests.DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(PolicyServiceTestCase, cls).setUpClass()

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        policies_registrar.register_policy_types(st2common)

        loader = fixtures.FixturesLoader()
        loader.save_fixtures_to_db(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)

    def setUp(self):
        super(PolicyServiceTestCase, self).setUp()

        params = {
            "action": "wolfpack.action-1",
            "parameters": {"actionstr": "foo-last"},
        }
        self.lv_ac_db_1 = action_db_models.LiveActionDB(**params)
        self.lv_ac_db_1, _ = action_service.request(self.lv_ac_db_1)

        params = {
            "action": "wolfpack.action-2",
            "parameters": {"actionstr": "foo-last"},
        }
        self.lv_ac_db_2 = action_db_models.LiveActionDB(**params)
        self.lv_ac_db_2, _ = action_service.request(self.lv_ac_db_2)

        params = {"action": "core.local", "parameters": {"cmd": "date"}}
        self.lv_ac_db_3 = action_db_models.LiveActionDB(**params)
        self.lv_ac_db_3, _ = action_service.request(self.lv_ac_db_3)

    def tearDown(self):
        action_service.update_status(
            self.lv_ac_db_1, action_constants.LIVEACTION_STATUS_CANCELED
        )
        action_service.update_status(
            self.lv_ac_db_2, action_constants.LIVEACTION_STATUS_CANCELED
        )
        action_service.update_status(
            self.lv_ac_db_3, action_constants.LIVEACTION_STATUS_CANCELED
        )

    def test_action_has_policies(self):
        self.assertTrue(policy_service.has_policies(self.lv_ac_db_1))

    def test_action_does_not_have_policies(self):
        self.assertFalse(policy_service.has_policies(self.lv_ac_db_3))

    def test_action_has_specific_policies(self):
        self.assertTrue(
            policy_service.has_policies(
                self.lv_ac_db_2,
                policy_types=policy_constants.POLICY_TYPES_REQUIRING_LOCK,
            )
        )

    def test_action_does_not_have_specific_policies(self):
        self.assertFalse(
            policy_service.has_policies(
                self.lv_ac_db_1,
                policy_types=policy_constants.POLICY_TYPES_REQUIRING_LOCK,
            )
        )
