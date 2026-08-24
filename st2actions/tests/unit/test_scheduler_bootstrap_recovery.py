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

"""
Test that verifies the scheduler bootstrap recovery mechanism for handling
LiveActions stuck in 'requested' status due to RabbitMQ failures.
"""

from __future__ import absolute_import

from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.util import date as date_utils
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader
import st2tests.config as tests_config
from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK
from st2actions.scheduler.handler import ActionExecutionSchedulingQueueHandler


TEST_FIXTURES = {"runners": ["run-local.yaml"], "actions": ["local.yaml"]}


class SchedulerBootstrapRecoveryTestCase(DbTestCase):
    """
    Test case to verify that the scheduler's bootstrap recovery mechanism
    can recover LiveActions stuck in 'requested' status due to RabbitMQ failures.
    """

    @classmethod
    def setUpClass(cls):
        super(SchedulerBootstrapRecoveryTestCase, cls).setUpClass()
        tests_config.reset()
        tests_config.parse_args()
        loader = FixturesLoader()
        loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )

    def setUp(self):
        super(SchedulerBootstrapRecoveryTestCase, self).setUp()

    def test_bootstrap_recovers_requested_liveaction_without_queue_entry(self):
        """
        Test that _bootstrap_missing_scheduling_queue_items creates a queue entry
        for a LiveAction in 'requested' status that doesn't have one.

        This simulates the scenario where RabbitMQ was down when the action was
        created, so the SchedulerEntrypoint never consumed the message.
        """
        # Create a LiveAction in 'requested' status directly in the database
        # (simulating what happens when publish_request fails due to RabbitMQ being down)
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.action = "core.local"
        liveaction_db.parameters = {"cmd": "echo 'test'"}
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()

        # Save directly to DB without publishing (simulating RabbitMQ failure)
        liveaction_db = LiveAction.add_or_update(liveaction_db, publish=False)

        # Create the associated ActionExecution
        from st2common.services import executions
        from st2common.util import action_db as action_utils

        action_db = action_utils.get_action_by_ref("core.local")
        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )
        execution_db = executions.create_execution_object(
            liveaction=liveaction_db,
            action_db=action_db,
            runnertype_db=runnertype_db,
            publish=False,
        )

        # Verify no queue entry exists
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(len(queue_items), 0, "Queue entry should not exist initially")

        # Run the bootstrap recovery
        handler = ActionExecutionSchedulingQueueHandler()
        handler._bootstrap_missing_scheduling_queue_items()

        # Verify queue entry was created
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(
            len(queue_items), 1, "Queue entry should be created by bootstrap"
        )

        queue_item = queue_items[0]
        self.assertEqual(queue_item.liveaction_id, str(liveaction_db.id))
        self.assertEqual(queue_item.action_execution_id, str(execution_db.id))
        self.assertIsNotNone(queue_item.scheduled_start_timestamp)
        self.assertIsNotNone(queue_item.original_start_timestamp)

    def test_bootstrap_skips_liveaction_with_existing_queue_entry(self):
        """
        Test that _bootstrap_missing_scheduling_queue_items doesn't create duplicate
        queue entries for LiveActions that already have them.
        """
        # Create a LiveAction with a queue entry (normal case)
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.action = "core.local"
        liveaction_db.parameters = {"cmd": "echo 'test2'"}
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db = LiveAction.add_or_update(liveaction_db, publish=False)

        # Create execution and queue entry
        from st2common.services import executions
        from st2common.util import action_db as action_utils
        from st2common.models.db.execution_queue import (
            ActionExecutionSchedulingQueueItemDB,
        )

        action_db = action_utils.get_action_by_ref("core.local")
        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )
        execution_db = executions.create_execution_object(
            liveaction=liveaction_db,
            action_db=action_db,
            runnertype_db=runnertype_db,
            publish=False,
        )

        # Manually create queue entry
        queue_item_db = ActionExecutionSchedulingQueueItemDB()
        queue_item_db.action_execution_id = str(execution_db.id)
        queue_item_db.liveaction_id = str(liveaction_db.id)
        queue_item_db.original_start_timestamp = liveaction_db.start_timestamp
        queue_item_db.scheduled_start_timestamp = liveaction_db.start_timestamp
        ActionExecutionSchedulingQueue.add_or_update(queue_item_db, publish=False)

        # Verify one queue entry exists
        queue_items_before = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(len(queue_items_before), 1)
        original_queue_item_id = str(queue_items_before[0].id)

        # Run the bootstrap recovery
        handler = ActionExecutionSchedulingQueueHandler()
        handler._bootstrap_missing_scheduling_queue_items()

        # Verify still only one queue entry exists (no duplicate created)
        queue_items_after = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(
            len(queue_items_after), 1, "Should not create duplicate queue entry"
        )
        self.assertEqual(str(queue_items_after[0].id), original_queue_item_id)

    def test_bootstrap_ignores_non_requested_status(self):
        """
        Test that _bootstrap_missing_scheduling_queue_items only processes
        LiveActions in 'requested' status, not 'delayed', 'scheduled', or other statuses.
        """
        statuses_to_test = [
            action_constants.LIVEACTION_STATUS_DELAYED,
            action_constants.LIVEACTION_STATUS_SCHEDULED,
            action_constants.LIVEACTION_STATUS_RUNNING,
            action_constants.LIVEACTION_STATUS_SUCCEEDED,
        ]

        created_liveactions = []
        for status in statuses_to_test:
            liveaction_db = LiveActionDB()
            liveaction_db.status = status
            liveaction_db.action = "core.local"
            liveaction_db.parameters = {"cmd": f"echo '{status}'"}
            liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
            liveaction_db = LiveAction.add_or_update(liveaction_db, publish=False)
            created_liveactions.append(liveaction_db)

            # Create execution but no queue entry
            from st2common.services import executions
            from st2common.util import action_db as action_utils

            action_db = action_utils.get_action_by_ref("core.local")
            runnertype_db = action_utils.get_runnertype_by_name(
                action_db.runner_type["name"]
            )
            executions.create_execution_object(
                liveaction=liveaction_db,
                action_db=action_db,
                runnertype_db=runnertype_db,
                publish=False,
            )

        # Run the bootstrap recovery
        handler = ActionExecutionSchedulingQueueHandler()
        handler._bootstrap_missing_scheduling_queue_items()

        # Verify no queue entries were created for non-requested statuses
        for liveaction_db in created_liveactions:
            queue_items = ActionExecutionSchedulingQueue.query(
                liveaction_id=str(liveaction_db.id)
            )
            self.assertEqual(
                len(queue_items),
                0,
                f"No queue entry should be created for status '{liveaction_db.status}'",
            )

    def test_bootstrap_handles_liveaction_without_execution(self):
        """
        Test that _bootstrap_missing_scheduling_queue_items gracefully handles
        the case where a LiveAction exists but its ActionExecution doesn't.
        """
        # Create a LiveAction without an ActionExecution (edge case)
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.action = "core.local"
        liveaction_db.parameters = {"cmd": "echo 'orphan'"}
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db = LiveAction.add_or_update(liveaction_db, publish=False)

        # Don't create an ActionExecution - this is the edge case

        # Run the bootstrap recovery - should not crash
        handler = ActionExecutionSchedulingQueueHandler()
        handler._bootstrap_missing_scheduling_queue_items()

        # Verify no queue entry was created (since there's no execution)
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(
            len(queue_items), 0, "No queue entry should be created without execution"
        )

    def test_bootstrap_preserves_delay_field(self):
        """
        Test that _bootstrap_missing_scheduling_queue_items correctly handles
        the delay field when creating queue entries.
        """
        # Create a LiveAction with a delay
        delay_ms = 5000  # 5 seconds
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.action = "core.local"
        liveaction_db.parameters = {"cmd": "echo 'delayed'"}
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
        liveaction_db.delay = delay_ms
        liveaction_db = LiveAction.add_or_update(liveaction_db, publish=False)

        # Create execution
        from st2common.services import executions
        from st2common.util import action_db as action_utils

        action_db = action_utils.get_action_by_ref("core.local")
        runnertype_db = action_utils.get_runnertype_by_name(
            action_db.runner_type["name"]
        )
        executions.create_execution_object(
            liveaction=liveaction_db,
            action_db=action_db,
            runnertype_db=runnertype_db,
            publish=False,
        )

        # Run the bootstrap recovery
        handler = ActionExecutionSchedulingQueueHandler()
        handler._bootstrap_missing_scheduling_queue_items()

        # Verify queue entry was created with correct delay
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(len(queue_items), 1)

        queue_item = queue_items[0]
        self.assertEqual(queue_item.delay, delay_ms)

        # Verify scheduled_start_timestamp is offset by the delay
        expected_scheduled_time = date_utils.append_milliseconds_to_time(
            liveaction_db.start_timestamp, delay_ms
        )
        self.assertEqual(queue_item.scheduled_start_timestamp, expected_scheduled_time)
