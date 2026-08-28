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
Test that verifies the scheduler shuts down completely when RabbitMQ
connection failures exhaust retry attempts.
"""

from __future__ import absolute_import

import eventlet
import mock
from kombu import exceptions as kombu_exceptions

from st2tests.base import DbTestCase
import st2tests.config as tests_config
from st2actions.cmd import scheduler


class SchedulerShutdownOnRabbitMQFailureTestCase(DbTestCase):
    """
    Test case to verify that when the scheduler's entrypoint consumer fails
    due to RabbitMQ connection exhaustion, the entire scheduler process
    shuts down cleanly.
    """

    def setUp(self):
        super(SchedulerShutdownOnRabbitMQFailureTestCase, self).setUp()
        tests_config.reset()
        tests_config.parse_args()

    @mock.patch("st2actions.scheduler.entrypoint.get_scheduler_entrypoint")
    @mock.patch("st2actions.scheduler.handler.get_handler")
    def test_scheduler_shuts_down_when_entrypoint_consumer_fails(
        self, mock_get_handler, mock_get_entrypoint
    ):
        """
        Test that when the entrypoint consumer thread fails with KombuError
        after exhausting retry attempts, the scheduler:
        1. Detects the failure via eventlet.wait_all()
        2. Calls shutdown() on both handler and entrypoint
        3. Re-raises the exception to exit the process
        """
        # Create mock handler with threads that would run forever
        mock_handler = mock.MagicMock()
        mock_handler_main_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_handler_cleanup_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_handler._main_thread = mock_handler_main_thread
        mock_handler._cleanup_thread = mock_handler_cleanup_thread
        mock_get_handler.return_value = mock_handler

        # Create mock entrypoint with a consumer thread that fails immediately
        mock_entrypoint = mock.MagicMock()

        # Simulate consumer thread failing with OperationalError (RabbitMQ connection exhausted)
        def failing_consumer():
            raise kombu_exceptions.OperationalError("[Errno 111] ECONNREFUSED")

        mock_entrypoint_consumer_thread = eventlet.spawn(failing_consumer)
        mock_entrypoint._consumer_thread = mock_entrypoint_consumer_thread
        mock_get_entrypoint.return_value = mock_entrypoint

        # Run the scheduler and expect it to raise the exception
        with self.assertRaises(kombu_exceptions.OperationalError) as cm:
            scheduler._run_scheduler()

        # Verify the exception message
        self.assertIn("ECONNREFUSED", str(cm.exception))

        # Verify that shutdown was called on both components
        mock_handler.shutdown.assert_called_once()
        mock_entrypoint.shutdown.assert_called_once()

    @mock.patch("st2actions.scheduler.entrypoint.get_scheduler_entrypoint")
    @mock.patch("st2actions.scheduler.handler.get_handler")
    def test_scheduler_shuts_down_when_handler_main_thread_fails(
        self, mock_get_handler, mock_get_entrypoint
    ):
        """
        Test that when the handler's main thread fails, the scheduler
        detects it and shuts down both components.
        """
        # Create mock handler with main thread that fails
        mock_handler = mock.MagicMock()

        def failing_main_thread():
            raise RuntimeError("Handler main thread failed")

        mock_handler_main_thread = eventlet.spawn(failing_main_thread)
        mock_handler_cleanup_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_handler._main_thread = mock_handler_main_thread
        mock_handler._cleanup_thread = mock_handler_cleanup_thread
        mock_get_handler.return_value = mock_handler

        # Create mock entrypoint that would run forever
        mock_entrypoint = mock.MagicMock()
        mock_entrypoint_consumer_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_entrypoint._consumer_thread = mock_entrypoint_consumer_thread
        mock_get_entrypoint.return_value = mock_entrypoint

        # Run the scheduler and expect it to raise the exception
        with self.assertRaises(RuntimeError) as cm:
            scheduler._run_scheduler()

        # Verify the exception message
        self.assertIn("Handler main thread failed", str(cm.exception))

        # Verify that shutdown was called on both components
        mock_handler.shutdown.assert_called_once()
        mock_entrypoint.shutdown.assert_called_once()

    @mock.patch("st2actions.scheduler.entrypoint.get_scheduler_entrypoint")
    @mock.patch("st2actions.scheduler.handler.get_handler")
    def test_scheduler_shuts_down_when_handler_cleanup_thread_fails(
        self, mock_get_handler, mock_get_entrypoint
    ):
        """
        Test that when the handler's cleanup thread fails, the scheduler
        detects it and shuts down both components.
        """
        # Create mock handler with cleanup thread that fails
        mock_handler = mock.MagicMock()
        mock_handler_main_thread = eventlet.spawn(lambda: eventlet.sleep(1000))

        def failing_cleanup_thread():
            raise RuntimeError("Handler cleanup thread failed")

        mock_handler_cleanup_thread = eventlet.spawn(failing_cleanup_thread)
        mock_handler._main_thread = mock_handler_main_thread
        mock_handler._cleanup_thread = mock_handler_cleanup_thread
        mock_get_handler.return_value = mock_handler

        # Create mock entrypoint that would run forever
        mock_entrypoint = mock.MagicMock()
        mock_entrypoint_consumer_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_entrypoint._consumer_thread = mock_entrypoint_consumer_thread
        mock_get_entrypoint.return_value = mock_entrypoint

        # Run the scheduler and expect it to raise the exception
        with self.assertRaises(RuntimeError) as cm:
            scheduler._run_scheduler()

        # Verify the exception message
        self.assertIn("Handler cleanup thread failed", str(cm.exception))

        # Verify that shutdown was called on both components
        mock_handler.shutdown.assert_called_once()
        mock_entrypoint.shutdown.assert_called_once()

    @mock.patch("st2actions.scheduler.entrypoint.get_scheduler_entrypoint")
    @mock.patch("st2actions.scheduler.handler.get_handler")
    def test_scheduler_connection_error_propagates(
        self, mock_get_handler, mock_get_entrypoint
    ):
        """
        Test that ConnectionError (a subclass of OperationalError) also
        triggers proper shutdown.
        """
        # Create mock handler with threads that would run forever
        mock_handler = mock.MagicMock()
        mock_handler_main_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_handler_cleanup_thread = eventlet.spawn(lambda: eventlet.sleep(1000))
        mock_handler._main_thread = mock_handler_main_thread
        mock_handler._cleanup_thread = mock_handler_cleanup_thread
        mock_get_handler.return_value = mock_handler

        # Create mock entrypoint with consumer thread that fails with ConnectionError
        mock_entrypoint = mock.MagicMock()

        def failing_consumer():
            raise kombu_exceptions.ConnectionError("Connection lost")

        mock_entrypoint_consumer_thread = eventlet.spawn(failing_consumer)
        mock_entrypoint._consumer_thread = mock_entrypoint_consumer_thread
        mock_get_entrypoint.return_value = mock_entrypoint

        # Run the scheduler and expect it to raise the exception
        with self.assertRaises(kombu_exceptions.ConnectionError) as cm:
            scheduler._run_scheduler()

        # Verify the exception message
        self.assertIn("Connection lost", str(cm.exception))

        # Verify that shutdown was called on both components
        mock_handler.shutdown.assert_called_once()
        mock_entrypoint.shutdown.assert_called_once()
