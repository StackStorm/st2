# Copyright 2020 The StackStorm Authors.
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
Tests to verify that st2reactor rulesengine properly shuts down when RabbitMQ
connection failures occur, rather than hanging indefinitely.
"""

from __future__ import absolute_import

import mock

from kombu.exceptions import OperationalError as KombuOperationalError

from st2common.util import concurrency
from st2reactor.cmd.rulesengine import _run_worker
from st2reactor.rules.worker import TriggerInstanceDispatcher
from st2tests.base import CleanDbTestCase

__all__ = ["RulesEngineShutdownOnRabbitMQFailureTestCase"]


class RulesEngineShutdownOnRabbitMQFailureTestCase(CleanDbTestCase):
    """
    Test cases to ensure the rulesengine service exits cleanly when RabbitMQ
    connection issues occur, preventing infinite hangs.
    """

    @mock.patch("st2reactor.rules.worker.transport_utils.get_connection")
    def test_rulesengine_connection_error_propagates(self, mock_get_connection):
        """
        Test that connection errors during worker initialization propagate
        and cause the service to exit.
        """
        # Simulate connection failure during worker.get_worker()
        mock_get_connection.side_effect = KombuOperationalError("Connection refused")

        # Run the worker in a greenthread
        run_thread = concurrency.spawn(_run_worker)

        # The worker should raise the connection error
        with self.assertRaises(KombuOperationalError) as cm:
            concurrency.wait(run_thread)

        self.assertIn("Connection refused", str(cm.exception))

    @mock.patch.object(TriggerInstanceDispatcher, "start")
    @mock.patch.object(TriggerInstanceDispatcher, "shutdown")
    def test_rulesengine_shuts_down_when_worker_thread_fails(
        self, mock_shutdown, mock_start
    ):
        """
        Test that when the worker thread fails with an exception,
        the rulesengine detects it, shuts down cleanly, and raises the exception.
        """

        def mock_start_that_fails():
            # Simulate the worker thread starting but then failing
            concurrency.sleep(0.1)
            raise RuntimeError("Worker thread failed")

        mock_start.side_effect = mock_start_that_fails

        # Run the worker
        run_thread = concurrency.spawn(_run_worker)

        # Should raise the RuntimeError from the worker thread
        with self.assertRaises(RuntimeError) as cm:
            concurrency.wait(run_thread)

        self.assertIn("Worker thread failed", str(cm.exception))

        # Shutdown should have been called
        mock_shutdown.assert_called_once()

    @mock.patch("st2reactor.rules.worker.transport_utils.get_connection")
    @mock.patch.object(TriggerInstanceDispatcher, "shutdown")
    def test_rulesengine_handles_connection_retry_exhaustion(
        self, mock_shutdown, mock_get_connection
    ):
        """
        Test that when connection retries are exhausted (after max attempts),
        the rulesengine exits cleanly with an exception.
        """
        # Mock connection to fail during worker initialization
        mock_get_connection.side_effect = KombuOperationalError(
            "Failed to connect after 10 attempts"
        )

        run_thread = concurrency.spawn(_run_worker)

        # Should raise the connection error
        with self.assertRaises(KombuOperationalError) as cm:
            concurrency.wait(run_thread)

        self.assertIn("Failed to connect", str(cm.exception))
