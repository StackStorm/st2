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

import eventlet
import mock

from st2actions.cmd.scheduler import _run_scheduler
from st2actions.scheduler.handler import ActionExecutionSchedulingQueueHandler
from st2actions.scheduler.entrypoint import SchedulerEntrypoint

from st2tests.base import CleanDbTestCase

__all__ = ["SchedulerServiceEntryPointTestCase"]


def mock_handler_run(self):
    # NOTE: We use eventlet.sleep to emulate async nature of this process
    eventlet.sleep(0.2)
    raise Exception("handler run exception")


def mock_handler_cleanup(self):
    # NOTE: We use eventlet.sleep to emulate async nature of this process
    eventlet.sleep(0.2)
    raise Exception("handler clean exception")


def mock_entrypoint_start(self):
    # NOTE: We use eventlet.sleep to emulate async nature of this process
    eventlet.sleep(0.2)
    raise Exception("entrypoint start exception")


class SchedulerServiceEntryPointTestCase(CleanDbTestCase):
    @mock.patch.object(ActionExecutionSchedulingQueueHandler, "run", mock_handler_run)
    @mock.patch("st2actions.cmd.scheduler.LOG")
    def test_service_exits_correctly_on_fatal_exception_in_handler_run(self, mock_log):
        run_thread = eventlet.spawn(_run_scheduler)
        result = run_thread.wait()

        self.assertEqual(result, 1)

        mock_log_exception_call = mock_log.exception.call_args_list[0][0][0]
        self.assertIn("Scheduler unexpectedly stopped", mock_log_exception_call)

    @mock.patch.object(
        ActionExecutionSchedulingQueueHandler, "cleanup", mock_handler_cleanup
    )
    @mock.patch("st2actions.cmd.scheduler.LOG")
    def test_service_exits_correctly_on_fatal_exception_in_handler_cleanup(
        self, mock_log
    ):
        run_thread = eventlet.spawn(_run_scheduler)
        result = run_thread.wait()

        self.assertEqual(result, 1)

        mock_log_exception_call = mock_log.exception.call_args_list[0][0][0]
        self.assertIn("Scheduler unexpectedly stopped", mock_log_exception_call)

    @mock.patch.object(SchedulerEntrypoint, "start", mock_entrypoint_start)
    @mock.patch("st2actions.cmd.scheduler.LOG")
    def test_service_exits_correctly_on_fatal_exception_in_entrypoint_start(
        self, mock_log
    ):
        run_thread = eventlet.spawn(_run_scheduler)
        result = run_thread.wait()

        self.assertEqual(result, 1)

        mock_log_exception_call = mock_log.exception.call_args_list[0][0][0]
        self.assertIn("Scheduler unexpectedly stopped", mock_log_exception_call)
