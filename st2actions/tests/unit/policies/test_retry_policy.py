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

import st2actions
from st2common.constants.action import LIVEACTION_STATUS_REQUESTED
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.action import LIVEACTION_STATUS_SCHEDULED
from st2common.constants.action import LIVEACTION_STATUS_DELAYED
from st2common.constants.action import LIVEACTION_STATUS_CANCELING
from st2common.constants.action import LIVEACTION_STATUS_CANCELED
from st2common.bootstrap.policiesregistrar import register_policy_types
from st2common.bootstrap import runnersregistrar as runners_registrar
from st2common.models.db.action import LiveActionDB
from st2common.persistence.action import LiveAction, ActionExecution
from st2common.services import action as action_service
from st2common.services import trace as trace_service
from st2actions.policies.retry import ExecutionRetryPolicyApplicator
from st2tests.base import DbTestCase
from st2tests.base import CleanDbTestCase
from st2tests.fixtures.generic.fixture import PACK_NAME as PACK
from st2tests.fixturesloader import FixturesLoader

__all__ = ["RetryPolicyTestCase"]

TEST_FIXTURES = {"actions": ["action1.yaml"], "policies": ["policy_4.yaml"]}


class RetryPolicyTestCase(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        DbTestCase.setUpClass()
        super(RetryPolicyTestCase, cls).setUpClass()

    def setUp(self):
        super(RetryPolicyTestCase, self).setUp()

        # Register runners
        runners_registrar.register_runners()

        # Register common policy types
        register_policy_types(st2actions)

        loader = FixturesLoader()
        models = loader.save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES
        )

        # Instantiate policy applicator we will use in the tests
        policy_db = models["policies"]["policy_4.yaml"]
        retry_on = policy_db.parameters["retry_on"]
        max_retry_count = policy_db.parameters["max_retry_count"]
        self.policy = ExecutionRetryPolicyApplicator(
            policy_ref="test_policy",
            policy_type="action.retry",
            retry_on=retry_on,
            max_retry_count=max_retry_count,
            delay=0,
        )

    def test_retry_on_timeout_no_retry_since_no_timeout_reached(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which succeeds
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_SUCCEEDED
        execution_db.status = LIVEACTION_STATUS_SUCCEEDED
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should only be 1 object since the action didn't timeout and therefore it wasn't
        # retried
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 1)
        self.assertEqual(len(action_execution_dbs), 1)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_SUCCEEDED)

    def test_retry_on_timeout_first_retry_is_successful(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be two objects - original execution and retried execution
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 2)
        self.assertEqual(len(action_execution_dbs), 2)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(action_execution_dbs[1].status, LIVEACTION_STATUS_REQUESTED)

        # Verify retried execution contains policy related context
        original_liveaction_id = action_execution_dbs[0].liveaction["id"]

        context = action_execution_dbs[1].context
        self.assertIn("policies", context)
        self.assertEqual(context["policies"]["retry"]["retry_count"], 1)
        self.assertEqual(context["policies"]["retry"]["applied_policy"], "test_policy")
        self.assertEqual(
            context["policies"]["retry"]["retried_liveaction_id"],
            original_liveaction_id,
        )

        # Simulate success of second action so no it shouldn't be retried anymore
        live_action_db = live_action_dbs[1]
        live_action_db.status = LIVEACTION_STATUS_SUCCEEDED
        LiveAction.add_or_update(live_action_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be no new object since action succeeds so no retry was attempted
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 2)
        self.assertEqual(len(action_execution_dbs), 2)
        self.assertEqual(live_action_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(live_action_dbs[1].status, LIVEACTION_STATUS_SUCCEEDED)

    def test_retry_on_timeout_policy_is_retried_twice(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be two objects - original execution and retried execution
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 2)
        self.assertEqual(len(action_execution_dbs), 2)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(action_execution_dbs[1].status, LIVEACTION_STATUS_REQUESTED)

        # Verify retried execution contains policy related context
        original_liveaction_id = action_execution_dbs[0].liveaction["id"]

        context = action_execution_dbs[1].context
        self.assertIn("policies", context)
        self.assertEqual(context["policies"]["retry"]["retry_count"], 1)
        self.assertEqual(context["policies"]["retry"]["applied_policy"], "test_policy")
        self.assertEqual(
            context["policies"]["retry"]["retried_liveaction_id"],
            original_liveaction_id,
        )

        # Simulate timeout of second action which should cause another retry
        live_action_db = live_action_dbs[1]
        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)

        execution_db = action_execution_dbs[1]
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # There should be three objects - original execution and 2 retried executions
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 3)
        self.assertEqual(len(action_execution_dbs), 3)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(action_execution_dbs[1].status, LIVEACTION_STATUS_TIMED_OUT)
        self.assertEqual(action_execution_dbs[2].status, LIVEACTION_STATUS_REQUESTED)

        # Verify retried execution contains policy related context
        original_liveaction_id = action_execution_dbs[1].liveaction["id"]

        context = action_execution_dbs[2].context
        self.assertIn("policies", context)
        self.assertEqual(context["policies"]["retry"]["retry_count"], 2)
        self.assertEqual(context["policies"]["retry"]["applied_policy"], "test_policy")
        self.assertEqual(
            context["policies"]["retry"]["retried_liveaction_id"],
            original_liveaction_id,
        )

    def test_retry_on_timeout_max_retries_reached(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        liveaction = LiveActionDB(
            action="wolfpack.action-1", parameters={"actionstr": "foo"}
        )
        live_action_db, execution_db = action_service.request(liveaction)

        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        live_action_db.context["policies"] = {}
        live_action_db.context["policies"]["retry"] = {"retry_count": 2}
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # Note: There should be no new objects since max retries has been reached
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 1)
        self.assertEqual(len(action_execution_dbs), 1)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)

    @mock.patch.object(
        trace_service,
        "get_trace_db_by_live_action",
        mock.MagicMock(return_value=(None, None)),
    )
    def test_no_retry_on_workflow_task(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action which times out
        live_action_db = LiveActionDB(
            action="wolfpack.action-1",
            parameters={"actionstr": "foo"},
            context={"parent": {"execution_id": "abcde"}},
        )

        live_action_db, execution_db = action_service.request(live_action_db)
        live_action_db = LiveAction.get_by_id(str(live_action_db.id))
        self.assertEqual(live_action_db.status, LIVEACTION_STATUS_REQUESTED)

        # Expire the workflow instance.
        live_action_db.status = LIVEACTION_STATUS_TIMED_OUT
        live_action_db.context["policies"] = {}
        execution_db.status = LIVEACTION_STATUS_TIMED_OUT
        LiveAction.add_or_update(live_action_db)
        ActionExecution.add_or_update(execution_db)

        # Simulate policy "apply_after" run
        self.policy.apply_after(target=live_action_db)

        # Note: There should be no new objects since live action is under the context of a workflow.
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), 1)
        self.assertEqual(len(action_execution_dbs), 1)
        self.assertEqual(action_execution_dbs[0].status, LIVEACTION_STATUS_TIMED_OUT)

    def test_no_retry_on_non_applicable_statuses(self):
        # Verify initial state
        self.assertSequenceEqual(LiveAction.get_all(), [])
        self.assertSequenceEqual(ActionExecution.get_all(), [])

        # Start a mock action in various statuses in which we shouldn't retry
        non_retry_statuses = [
            LIVEACTION_STATUS_REQUESTED,
            LIVEACTION_STATUS_SCHEDULED,
            LIVEACTION_STATUS_DELAYED,
            LIVEACTION_STATUS_CANCELING,
            LIVEACTION_STATUS_CANCELED,
        ]

        action_ref = "wolfpack.action-1"

        for status in non_retry_statuses:
            liveaction = LiveActionDB(
                action=action_ref, parameters={"actionstr": "foo"}
            )
            live_action_db, execution_db = action_service.request(liveaction)

            live_action_db.status = status
            execution_db.status = status
            LiveAction.add_or_update(live_action_db)
            ActionExecution.add_or_update(execution_db)

            # Simulate policy "apply_after" run
            self.policy.apply_after(target=live_action_db)

        # None of the actions should have been retried
        live_action_dbs = LiveAction.get_all()
        action_execution_dbs = ActionExecution.get_all()
        self.assertEqual(len(live_action_dbs), len(non_retry_statuses))
        self.assertEqual(len(action_execution_dbs), len(non_retry_statuses))
