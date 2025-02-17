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
import mock

# This import must be early for import-time side-effects.
from st2tests.base import CleanDbTestCase, DbTestCase

import st2common
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.models.db.action import LiveActionDB
from st2common.persistence.policy import Policy
from st2common import policies
from st2common.services import action as action_service
from st2common.services import policies as policy_service
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader


__all__ = ["SchedulerPoliciesTestCase", "NotifierPoliciesTestCase"]


TEST_FIXTURES_1 = {
    "actions": ["action1.yaml"],
    "policies": [
        "policy_4.yaml",
    ],
}
TEST_FIXTURES_2 = {
    "actions": ["action1.yaml"],
    "policies": [
        "policy_1.yaml",
    ],
}


class SchedulerPoliciesTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        DbTestCase.setUpClass()
        super(SchedulerPoliciesTestCase, cls).setUpClass()

    def setUp(self):
        super(SchedulerPoliciesTestCase, self).setUp()

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        register_policy_types(st2common)

        loader = FixturesLoader()
        models = loader.save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES_2
        )

        # Policy with "post_run" application
        self.policy_db = models["policies"]["policy_1.yaml"]

    @mock.patch.object(policies, "get_driver", mock.MagicMock(return_value=None))
    def test_disabled_policy_not_applied_on_pre_run(self):
        ##########
        # First test a scenario where policy is enabled
        ##########
        self.assertTrue(self.policy_db.enabled)

        # Post run hasn't been called yet, call count should be 0
        self.assertEqual(policies.get_driver.call_count, 0)

        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)
        policy_service.apply_pre_run_policies(live_action_db)

        # Ony policy has been applied so call count should be 1
        self.assertEqual(policies.get_driver.call_count, 1)

        ##########
        # Now a scenaro with disabled policy
        ##########
        policies.get_driver.call_count = 0
        self.policy_db.enabled = False
        self.policy_db = Policy.add_or_update(self.policy_db)
        self.assertFalse(self.policy_db.enabled)

        self.assertEqual(policies.get_driver.call_count, 0)

        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)
        policy_service.apply_pre_run_policies(live_action_db)

        # Policy is disabled so call_count should stay the same as before as no policies have been
        # applied
        self.assertEqual(policies.get_driver.call_count, 0)


class NotifierPoliciesTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        DbTestCase.setUpClass()
        super(NotifierPoliciesTestCase, cls).setUpClass()

    def setUp(self):
        super(NotifierPoliciesTestCase, self).setUp()

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        register_policy_types(st2common)

        loader = FixturesLoader()
        models = loader.save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES_1
        )

        # Policy with "post_run" application
        self.policy_db = models["policies"]["policy_4.yaml"]

    @mock.patch.object(policies, "get_driver", mock.MagicMock(return_value=None))
    def test_disabled_policy_not_applied_on_post_run(self):
        ##########
        # First test a scenario where policy is enabled
        ##########
        self.assertTrue(self.policy_db.enabled)

        # Post run hasn't been called yet, call count should be 0
        self.assertEqual(policies.get_driver.call_count, 0)

        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)
        policy_service.apply_post_run_policies(live_action_db)

        # Ony policy has been applied so call count should be 1
        self.assertEqual(policies.get_driver.call_count, 1)

        ##########
        # Now a scenaro with disabled policy
        ##########
        policies.get_driver.call_count = 0
        self.policy_db.enabled = False
        self.policy_db = Policy.add_or_update(self.policy_db)
        self.assertFalse(self.policy_db.enabled)

        self.assertEqual(policies.get_driver.call_count, 0)

        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)
        policy_service.apply_post_run_policies(live_action_db)

        # Policy is disabled so call_count should stay the same as before as no policies have been
        # applied
        self.assertEqual(policies.get_driver.call_count, 0)
