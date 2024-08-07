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

# This import must be first for import-time side-effects.
from st2tests.base import CleanDbTestCase

import eventlet
import mock
import pymongo
import uuid

from st2actions.scheduler import handler
from st2common.models.db import execution_queue as ex_q_db
from st2common.persistence import execution_queue as ex_q_db_access


__all__ = ["SchedulerHandlerRetryTestCase"]


MOCK_QUEUE_ITEM = ex_q_db.ActionExecutionSchedulingQueueItemDB(
    liveaction_id=uuid.uuid4().hex
)


class SchedulerHandlerRetryTestCase(CleanDbTestCase):
    @mock.patch.object(
        handler.ActionExecutionSchedulingQueueHandler,
        "_get_next_execution",
        mock.MagicMock(
            side_effect=[pymongo.errors.ConnectionFailure(), MOCK_QUEUE_ITEM]
        ),
    )
    @mock.patch.object(eventlet.GreenPool, "spawn", mock.MagicMock(return_value=None))
    def test_handler_retry_connection_error(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()
        scheduling_queue_handler.process()

        # Make sure retry occurs and that _handle_execution in process is called.
        calls = [mock.call(scheduling_queue_handler._handle_execution, MOCK_QUEUE_ITEM)]
        eventlet.GreenPool.spawn.assert_has_calls(calls)

    @mock.patch.object(
        handler.ActionExecutionSchedulingQueueHandler,
        "_get_next_execution",
        mock.MagicMock(side_effect=[pymongo.errors.ConnectionFailure()] * 3),
    )
    @mock.patch.object(eventlet.GreenPool, "spawn", mock.MagicMock(return_value=None))
    def test_handler_retries_exhausted(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()
        self.assertRaises(
            pymongo.errors.ConnectionFailure, scheduling_queue_handler.process
        )
        self.assertEqual(eventlet.GreenPool.spawn.call_count, 0)

    @mock.patch.object(
        handler.ActionExecutionSchedulingQueueHandler,
        "_get_next_execution",
        mock.MagicMock(side_effect=KeyError()),
    )
    @mock.patch.object(eventlet.GreenPool, "spawn", mock.MagicMock(return_value=None))
    def test_handler_retry_unexpected_error(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()
        self.assertRaises(KeyError, scheduling_queue_handler.process)
        self.assertEqual(eventlet.GreenPool.spawn.call_count, 0)

    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "query",
        mock.MagicMock(
            side_effect=[pymongo.errors.ConnectionFailure(), [MOCK_QUEUE_ITEM]]
        ),
    )
    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "add_or_update",
        mock.MagicMock(return_value=None),
    )
    def test_handler_gc_retry_connection_error(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()
        scheduling_queue_handler._handle_garbage_collection()

        # Make sure retry occurs and that _handle_execution in process is called.
        calls = [mock.call(MOCK_QUEUE_ITEM, publish=False)]
        ex_q_db_access.ActionExecutionSchedulingQueue.add_or_update.assert_has_calls(
            calls
        )

    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "query",
        mock.MagicMock(side_effect=[pymongo.errors.ConnectionFailure()] * 3),
    )
    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "add_or_update",
        mock.MagicMock(return_value=None),
    )
    def test_handler_gc_retries_exhausted(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()

        self.assertRaises(
            pymongo.errors.ConnectionFailure,
            scheduling_queue_handler._handle_garbage_collection,
        )

        self.assertEqual(
            ex_q_db_access.ActionExecutionSchedulingQueue.add_or_update.call_count, 0
        )

    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "query",
        mock.MagicMock(side_effect=KeyError()),
    )
    @mock.patch.object(
        ex_q_db_access.ActionExecutionSchedulingQueue,
        "add_or_update",
        mock.MagicMock(return_value=None),
    )
    def test_handler_gc_unexpected_error(self):
        scheduling_queue_handler = handler.ActionExecutionSchedulingQueueHandler()

        self.assertRaises(KeyError, scheduling_queue_handler._handle_garbage_collection)

        self.assertEqual(
            ex_q_db_access.ActionExecutionSchedulingQueue.add_or_update.call_count, 0
        )
