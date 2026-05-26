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
Test that verifies the scheduler entrypoint calls bootstrap recovery when
RabbitMQ connection is revived after a failure.
"""

from __future__ import absolute_import

import mock

from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.execution_queue import ActionExecutionSchedulingQueue
from st2common.util import date as date_utils
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader
import st2tests.config as tests_config
from st2actions.scheduler.handler import ActionExecutionSchedulingQueueHandler
from st2actions.scheduler.entrypoint import SchedulerEntrypoint, SchedulerQueueConsumer
from st2common.transport.utils import get_connection
from st2common.transport.queues import ACTIONSCHEDULER_REQUEST_QUEUE


FIXTURES_PACK = "generic"
TEST_FIXTURES = {"runners": ["run-local.yaml"], "actions": ["local.yaml"]}


class SchedulerConnectionRevivalTestCase(DbTestCase):
    """
    Test case to verify that the scheduler's entrypoint calls bootstrap recovery
    when RabbitMQ connection is revived.
    """

    @classmethod
    def setUpClass(cls):
        super(SchedulerConnectionRevivalTestCase, cls).setUpClass()
        tests_config.reset()
        tests_config.parse_args()
        loader = FixturesLoader()
        loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )

    def setUp(self):
        super(SchedulerConnectionRevivalTestCase, self).setUp()

    def test_connection_revived_calls_bootstrap(self):
        """
        Test that on_connection_revived() calls bootstrap recovery on the handler.
        """
        # Create handler
        handler = ActionExecutionSchedulingQueueHandler()

        with get_connection() as conn:
            # Create custom queue consumer
            entrypoint = SchedulerEntrypoint(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
            queue_consumer = SchedulerQueueConsumer(
                conn, [ACTIONSCHEDULER_REQUEST_QUEUE], entrypoint, handler
            )

        # Mock the bootstrap method to track if it's called
        with mock.patch.object(
            handler, "_bootstrap_missing_scheduling_queue_items"
        ) as mock_bootstrap:
            # Simulate connection revival
            queue_consumer.on_connection_revived()

            # Verify bootstrap was called
            mock_bootstrap.assert_called_once()

    def test_connection_revived_recovers_stuck_liveaction(self):
        """
        Test that connection revival actually recovers a stuck LiveAction.

        Simulates the scenario:
        1. LiveAction created with status='requested'
        2. RabbitMQ connection drops before message is consumed
        3. No queue entry created
        4. RabbitMQ connection recovers
        5. on_connection_revived() should bootstrap the missing queue entry
        """
        # Create a LiveAction in 'requested' status without a queue entry
        # (simulating what happens during RabbitMQ outage)
        liveaction_db = LiveActionDB()
        liveaction_db.status = action_constants.LIVEACTION_STATUS_REQUESTED
        liveaction_db.action = "core.local"
        liveaction_db.parameters = {"cmd": "echo 'revival test'"}
        liveaction_db.start_timestamp = date_utils.get_datetime_utc_now()
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

        # Verify no queue entry exists (simulating RabbitMQ outage)
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(len(queue_items), 0, "Queue entry should not exist initially")

        # Create handler
        handler = ActionExecutionSchedulingQueueHandler()

        with get_connection() as conn:
            entrypoint = SchedulerEntrypoint(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
            queue_consumer = SchedulerQueueConsumer(
                conn, [ACTIONSCHEDULER_REQUEST_QUEUE], entrypoint, handler
            )

        # Simulate connection revival - this should trigger bootstrap
        queue_consumer.on_connection_revived()

        # Verify queue entry was created by bootstrap
        queue_items = ActionExecutionSchedulingQueue.query(
            liveaction_id=str(liveaction_db.id)
        )
        self.assertEqual(
            len(queue_items), 1, "Queue entry should be created by bootstrap"
        )

        queue_item = queue_items[0]
        self.assertEqual(queue_item.liveaction_id, str(liveaction_db.id))
        self.assertEqual(queue_item.action_execution_id, str(execution_db.id))

    def test_connection_revived_without_handler_does_not_crash(self):
        """
        Test that on_connection_revived() doesn't crash if handler is not set.
        This ensures graceful handling of edge cases.
        """
        with get_connection() as conn:
            entrypoint = SchedulerEntrypoint(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
            # Create queue consumer without handler - simulating edge case
            queue_consumer = SchedulerQueueConsumer(
                conn,
                [ACTIONSCHEDULER_REQUEST_QUEUE],
                entrypoint,
                scheduler_handler=None,
            )

        # Should not raise exception
        try:
            queue_consumer.on_connection_revived()
        except Exception as e:
            self.fail(f"on_connection_revived() should not crash without handler: {e}")

    def test_connection_revived_handles_bootstrap_exception(self):
        """
        Test that on_connection_revived() gracefully handles exceptions from bootstrap.
        """
        handler = ActionExecutionSchedulingQueueHandler()

        with get_connection() as conn:
            entrypoint = SchedulerEntrypoint(conn, [ACTIONSCHEDULER_REQUEST_QUEUE])
            queue_consumer = SchedulerQueueConsumer(
                conn, [ACTIONSCHEDULER_REQUEST_QUEUE], entrypoint, handler
            )

        # Mock bootstrap to raise an exception
        with mock.patch.object(
            handler,
            "_bootstrap_missing_scheduling_queue_items",
            side_effect=Exception("Bootstrap failed"),
        ):
            # Should not raise - exception should be caught and logged
            try:
                queue_consumer.on_connection_revived()
            except Exception as e:
                self.fail(
                    f"on_connection_revived() should handle bootstrap exceptions: {e}"
                )
