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
import unittest
from unittest.mock import Mock

from st2common.transport.connection_retry_wrapper import (
    ClusterRetryContext,
    ConnectionRetryWrapper,
)
from six.moves import range


class TestClusterRetryContext(unittest.TestCase):
    def test_single_node_cluster_retry(self):
        retry_context = ClusterRetryContext(cluster_size=1)
        should_stop, wait = retry_context.should_stop()
        self.assertFalse(should_stop, "Not done trying.")
        self.assertEqual(wait, 10)

        should_stop, wait = retry_context.should_stop()
        self.assertFalse(should_stop, "Not done trying.")
        self.assertEqual(wait, 10)

        should_stop, wait = retry_context.should_stop()
        self.assertTrue(should_stop, "Done trying.")
        self.assertEqual(wait, 0)

    def test_should_stop_second_channel_open_error_should_be_non_fatal(self):
        retry_context = ClusterRetryContext(cluster_size=1)

        e = Exception("(504) CHANNEL_ERROR - second 'channel.open' seen")
        should_stop, wait = retry_context.should_stop(e=e)
        self.assertFalse(should_stop)
        self.assertEqual(wait, 0)

        e = Exception("CHANNEL_ERROR - second 'channel.open' seen")
        should_stop, wait = retry_context.should_stop(e=e)
        self.assertFalse(should_stop)
        self.assertEqual(wait, 0)

    def test_multiple_node_cluster_retry(self):
        cluster_size = 3
        max_retries = 2
        # _max_attempts = cluster_size * (max_retries + 1) = 3 * 3 = 9
        # First attempt doesn't count as retry, so we have 9 total attempts (indices 0-8)
        last_index = (cluster_size * (max_retries + 1)) - 1

        retry_context = ClusterRetryContext(
            cluster_size=cluster_size, max_retries=max_retries
        )

        for i in range(last_index + 1):
            should_stop, wait = retry_context.should_stop()
            if i == last_index:
                self.assertTrue(should_stop, "Done trying.")
                self.assertEqual(wait, 0)
            else:
                self.assertFalse(should_stop, "Not done trying.")
                # on cluster boundaries the wait is longer. Short wait when switching
                # to a different server within a cluster.
                if (i + 1) % cluster_size == 0:
                    self.assertEqual(wait, 10)
                else:
                    self.assertEqual(wait, 0)

    def test_zero_node_cluster_retry(self):
        retry_context = ClusterRetryContext(cluster_size=0)
        should_stop, wait = retry_context.should_stop()
        self.assertTrue(should_stop, "Done trying.")
        self.assertEqual(wait, 0)


class TestConnectionRetryWrapper(unittest.TestCase):
    """Test cases for ConnectionRetryWrapper class"""

    def test_connection_channel_attribute_error_with_none_connection(self):
        """
        Test that ConnectionRetryWrapper handles AttributeError when connection.channel()
        is called on a NoneType object (when connection.connection is None).

        This reproduces the error:
        AttributeError: 'NoneType' object has no attribute 'channel'

        The retry wrapper should attempt retries and eventually raise the error
        after exhausting all retry attempts.
        """
        # Setup mock logger
        mock_logger = Mock()

        # Create ConnectionRetryWrapper with single node cluster
        # This will allow 3 attempts total: initial + 2 retries (max_retries=2)
        wrapper = ConnectionRetryWrapper(
            cluster_size=1, logger=mock_logger, max_retries=2
        )

        # Create mock connection that raises AttributeError when channel() is called
        mock_connection = Mock()
        mock_connection.channel.side_effect = AttributeError(
            "'NoneType' object has no attribute 'channel'"
        )
        mock_connection.close = Mock()
        mock_connection.ensure_connection = Mock()

        # Create a simple callback
        callback = Mock()

        # Execute and expect AttributeError to be raised after retries exhausted
        with self.assertRaises(AttributeError) as context:
            wrapper.run(connection=mock_connection, wrapped_callback=callback)

        # Verify the error message
        self.assertIn(
            "'NoneType' object has no attribute 'channel'", str(context.exception)
        )

        # Verify that channel() was called multiple times (initial + retries)
        # cluster_size=1, max_retries=2 means 3 total attempts
        self.assertEqual(mock_connection.channel.call_count, 3)

        # Verify connection.close() was called on each retry attempt (not on final failure)
        self.assertEqual(mock_connection.close.call_count, 2)

        # Verify ensure_connection was called on each retry
        self.assertEqual(mock_connection.ensure_connection.call_count, 2)

        # Verify callback was never called since channel() always failed
        callback.assert_not_called()

        # Verify error logging occurred
        mock_logger.error.assert_called()
        error_calls = [call for call in mock_logger.error.call_args_list]
        self.assertTrue(
            any(
                "Failed to execute operation after exhausting all retry attempts"
                in str(call)
                for call in error_calls
            ),
            "Expected error message about exhausted retries",
        )

    def test_connection_retry_wrapper_successful_after_initial_failure(self):
        """
        Test that ConnectionRetryWrapper successfully retries and completes
        when an initial AttributeError occurs but subsequent attempts succeed.
        """
        mock_logger = Mock()
        wrapper = ConnectionRetryWrapper(
            cluster_size=1, logger=mock_logger, max_retries=2
        )

        # Create mock connection that fails first, then succeeds
        mock_connection = Mock()
        mock_channel = Mock()

        # First call raises AttributeError, second call succeeds
        mock_connection.channel.side_effect = [
            AttributeError("'NoneType' object has no attribute 'channel'"),
            mock_channel,
        ]
        mock_connection.close = Mock()
        mock_connection.ensure_connection = Mock()

        # Create callback that should be called when channel is available
        callback = Mock()

        # Execute - should succeed on second attempt
        wrapper.run(connection=mock_connection, wrapped_callback=callback)

        # Verify channel() was called twice (failed once, succeeded once)
        self.assertEqual(mock_connection.channel.call_count, 2)

        # Verify callback was called once with successful channel
        callback.assert_called_once_with(
            connection=mock_connection, channel=mock_channel
        )

        # Verify connection was closed after first failure
        self.assertEqual(mock_connection.close.call_count, 1)

        # Verify ensure_connection was called after first failure
        self.assertEqual(mock_connection.ensure_connection.call_count, 1)

        # Verify channel was properly closed
        mock_channel.close.assert_called_once()

    def test_connection_retry_wrapper_handles_generic_exception(self):
        """
        Test that ConnectionRetryWrapper handles other exceptions properly
        and still attempts retries.
        """
        mock_logger = Mock()
        wrapper = ConnectionRetryWrapper(
            cluster_size=1, logger=mock_logger, max_retries=1
        )

        mock_connection = Mock()
        mock_connection.channel.side_effect = RuntimeError("Connection failed")
        mock_connection.close = Mock()
        mock_connection.ensure_connection = Mock()

        callback = Mock()

        # Execute and expect RuntimeError after retries exhausted
        with self.assertRaises(RuntimeError) as context:
            wrapper.run(connection=mock_connection, wrapped_callback=callback)

        self.assertIn("Connection failed", str(context.exception))

        # Verify retries occurred (initial + 1 retry = 2 attempts)
        self.assertEqual(mock_connection.channel.call_count, 2)
        self.assertEqual(mock_connection.close.call_count, 1)
        self.assertEqual(mock_connection.ensure_connection.call_count, 1)

    def test_connection_refused_error_during_ensure_connection(self):
        """
        Test that ConnectionRetryWrapper handles ConnectionRefusedError that occurs
        during ensure_connection (when RabbitMQ is down or unreachable).

        This reproduces the error:
        ConnectionRefusedError: [Errno 111] ECONNREFUSED

        The wrapper should attempt retries and eventually raise the error after
        exhausting retry attempts, rather than retrying indefinitely.
        """
        from kombu import exceptions as kombu_exceptions

        mock_logger = Mock()
        wrapper = ConnectionRetryWrapper(
            cluster_size=1, logger=mock_logger, max_retries=2, ensure_max_retries=3
        )

        mock_connection = Mock()
        # First call to channel() fails, triggering ensure_connection
        mock_connection.channel.side_effect = OSError("Connection failed")
        mock_connection.close = Mock()

        # ensure_connection raises KombuError wrapping ConnectionRefusedError
        mock_connection.ensure_connection.side_effect = kombu_exceptions.KombuError(
            "ConnectionRefusedError: [Errno 111] ECONNREFUSED"
        )

        callback = Mock()

        # Execute and expect KombuError to be raised after retries exhausted
        with self.assertRaises(kombu_exceptions.KombuError) as context:
            wrapper.run(connection=mock_connection, wrapped_callback=callback)

        # Verify the error message contains connection refused info
        self.assertIn("ECONNREFUSED", str(context.exception))

        # Verify channel() was called once (initial attempt that failed)
        self.assertEqual(mock_connection.channel.call_count, 1)

        # Verify connection.close() was called before trying to re-establish
        self.assertEqual(mock_connection.close.call_count, 1)

        # Verify ensure_connection was called once (and it failed with KombuError)
        self.assertEqual(mock_connection.ensure_connection.call_count, 1)

        # Verify callback was never called since connection failed
        callback.assert_not_called()

        # Verify error logging occurred
        mock_logger.error.assert_called()
        error_calls = [call for call in mock_logger.error.call_args_list]
        self.assertTrue(
            any(
                "Failed to re-establish connection to RabbitMQ" in str(call)
                for call in error_calls
            ),
            "Expected error message about failed connection re-establishment",
        )

    def test_connection_refused_during_channel_creation(self):
        """
        Test ConnectionRefusedError raised directly during channel creation.
        """
        mock_logger = Mock()
        wrapper = ConnectionRetryWrapper(
            cluster_size=1, logger=mock_logger, max_retries=1
        )

        mock_connection = Mock()
        # Simulate ConnectionRefusedError during channel creation
        mock_connection.channel.side_effect = ConnectionRefusedError(
            111, "ECONNREFUSED"
        )
        mock_connection.close = Mock()
        mock_connection.ensure_connection = Mock()

        callback = Mock()

        # Execute and expect ConnectionRefusedError after retries exhausted
        with self.assertRaises(ConnectionRefusedError) as context:
            wrapper.run(connection=mock_connection, wrapped_callback=callback)

        self.assertIn("ECONNREFUSED", str(context.exception))

        # Verify retries occurred (initial + 1 retry = 2 attempts)
        self.assertEqual(mock_connection.channel.call_count, 2)
        self.assertEqual(mock_connection.close.call_count, 1)
        self.assertEqual(mock_connection.ensure_connection.call_count, 1)
