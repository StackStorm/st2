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
from kombu.message import Message

# This import must be early for import-time side-effects.
from st2tests.base import ExecutionDbTestCase

from st2actions import worker
from st2actions.scheduler import entrypoint as scheduling
from st2actions.scheduler import handler as scheduling_queue
from st2actions.container.base import RunnerContainer
from st2common.bootstrap import actionsregistrar
from st2common.bootstrap import runnersregistrar
from st2common.constants import action as action_constants
from st2common.models.db.liveaction import LiveActionDB
from st2common.persistence import action
from st2common.services import executions
from st2common.transport.publishers import PoolPublisher
from st2common.util import action_db as action_utils
from st2common.util import date as date_utils
from st2tests.fixtures.packs.core.fixture import PACK_PATH as CORE_PACK_PATH


PACKS = [CORE_PACK_PATH]


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
@mock.patch.object(executions, "update_execution", mock.MagicMock())
@mock.patch.object(Message, "ack", mock.MagicMock())
class QueueConsumerTest(ExecutionDbTestCase):
    @classmethod
    def setUpClass(cls):
        super(QueueConsumerTest, cls).setUpClass()

        # Register runners.
        runnersregistrar.register_runners()

        # Register test pack(s).
        actions_registrar = actionsregistrar.ActionsRegistrar(
            use_pack_cache=False, fail_on_failure=True
        )

        for pack in PACKS:
            actions_registrar.register_from_pack(pack)

    def __init__(self, *args, **kwargs):
        super(QueueConsumerTest, self).__init__(*args, **kwargs)
        self.scheduler = scheduling.get_scheduler_entrypoint()
        self.scheduling_queue = scheduling_queue.get_handler()
        self.dispatcher = worker.get_worker()

    def _create_liveaction_db(
        self, status=action_constants.LIVEACTION_STATUS_REQUESTED
    ):
        action_db = action_utils.get_action_by_ref("core.noop")

        liveaction_db = LiveActionDB(
            action=action_db.ref,
            parameters=None,
            start_timestamp=date_utils.get_datetime_utc_now(),
            status=status,
        )

        liveaction_db = action.LiveAction.add_or_update(liveaction_db, publish=False)
        executions.create_execution_object(liveaction_db)

        return liveaction_db

    def _process_request(self, liveaction_db):
        self.scheduler._queue_consumer._process_message(liveaction_db)
        queued_request = self.scheduling_queue._get_next_execution()
        self.scheduling_queue._handle_execution(queued_request)

    @mock.patch.object(
        RunnerContainer, "dispatch", mock.MagicMock(return_value={"key": "value"})
    )
    def test_execute(self):
        liveaction_db = self._create_liveaction_db()
        self._process_request(liveaction_db)

        scheduled_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        scheduled_liveaction_db = self._wait_on_status(
            scheduled_liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED
        )
        self.assertDictEqual(scheduled_liveaction_db.runner_info, {})

        self.dispatcher._queue_consumer._process_message(scheduled_liveaction_db)
        dispatched_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        self.assertGreater(len(list(dispatched_liveaction_db.runner_info.keys())), 0)
        self.assertEqual(
            dispatched_liveaction_db.status, action_constants.LIVEACTION_STATUS_RUNNING
        )

    @mock.patch.object(
        RunnerContainer, "dispatch", mock.MagicMock(side_effect=Exception("Boom!"))
    )
    def test_execute_failure(self):
        liveaction_db = self._create_liveaction_db()
        self._process_request(liveaction_db)

        scheduled_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        scheduled_liveaction_db = self._wait_on_status(
            scheduled_liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED
        )

        self.dispatcher._queue_consumer._process_message(scheduled_liveaction_db)
        dispatched_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        self.assertEqual(
            dispatched_liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED
        )

    @mock.patch.object(RunnerContainer, "dispatch", mock.MagicMock(return_value=None))
    def test_execute_no_result(self):
        liveaction_db = self._create_liveaction_db()
        self._process_request(liveaction_db)

        scheduled_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        scheduled_liveaction_db = self._wait_on_status(
            scheduled_liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED
        )

        self.dispatcher._queue_consumer._process_message(scheduled_liveaction_db)
        dispatched_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        self.assertEqual(
            dispatched_liveaction_db.status, action_constants.LIVEACTION_STATUS_FAILED
        )

    @mock.patch.object(RunnerContainer, "dispatch", mock.MagicMock(return_value=None))
    def test_execute_cancelation(self):
        liveaction_db = self._create_liveaction_db()
        self._process_request(liveaction_db)

        scheduled_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        scheduled_liveaction_db = self._wait_on_status(
            scheduled_liveaction_db, action_constants.LIVEACTION_STATUS_SCHEDULED
        )

        action_utils.update_liveaction_status(
            status=action_constants.LIVEACTION_STATUS_CANCELED,
            liveaction_id=liveaction_db.id,
        )

        canceled_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)
        self.dispatcher._queue_consumer._process_message(canceled_liveaction_db)
        dispatched_liveaction_db = action_utils.get_liveaction_by_id(liveaction_db.id)

        self.assertEqual(
            dispatched_liveaction_db.status, action_constants.LIVEACTION_STATUS_CANCELED
        )

        self.assertDictEqual(
            dispatched_liveaction_db.result,
            {"message": "Action execution canceled by user."},
        )
