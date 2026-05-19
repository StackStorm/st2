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
import mock

from oslo_config import cfg

from st2common.transport.connection_retry_mixin import ConnectionRetryMixin
from st2tests.config import parse_args

parse_args()


class MockConsumer(ConnectionRetryMixin):
    """Mock consumer class for testing the mixin."""

    def __init__(self):
        self._init_connection_retry()


class ConnectionRetryMixinTestCase(unittest.TestCase):
    def setUp(self):
        # Store original config value
        self._original_max_retries = cfg.CONF.messaging.connection_retry_max_attempts

    def tearDown(self):
        # Restore original config value
        cfg.CONF.set_override(
            "connection_retry_max_attempts",
            self._original_max_retries,
            group="messaging",
        )

    def test_init_connection_retry(self):
        """Test that initialization sets up retry tracking correctly."""
        consumer = MockConsumer()
        self.assertEqual(consumer._connection_retry_count, 0)
        self.assertEqual(
            consumer._max_connection_retries,
            cfg.CONF.messaging.connection_retry_max_attempts,
        )

    def test_on_connection_error_within_limit(self):
        """Test that connection errors within retry limit are logged but don't raise."""
        cfg.CONF.set_override("connection_retry_max_attempts", 5, group="messaging")
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # Should not raise for first few attempts
        for i in range(4):
            consumer.on_connection_error(exc, 1.0)
            self.assertEqual(consumer._connection_retry_count, i + 1)

    def test_on_connection_error_exceeds_limit(self):
        """Test that connection errors exceeding retry limit raise exception."""
        cfg.CONF.set_override("connection_retry_max_attempts", 3, group="messaging")
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # Should not raise for attempts within limit
        consumer.on_connection_error(exc, 1.0)
        consumer.on_connection_error(exc, 1.0)
        self.assertEqual(consumer._connection_retry_count, 2)

        # Should raise when exceeding limit
        with self.assertRaises(Exception) as ctx:
            consumer.on_connection_error(exc, 1.0)

        self.assertEqual(str(ctx.exception), "Connection failed")
        self.assertEqual(consumer._connection_retry_count, 3)

    def test_on_connection_error_unlimited_retries(self):
        """Test that setting max_retries to 0 allows unlimited retries."""
        cfg.CONF.set_override("connection_retry_max_attempts", 0, group="messaging")
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # Should not raise even after many attempts
        for i in range(100):
            consumer.on_connection_error(exc, 1.0)
            self.assertEqual(consumer._connection_retry_count, i + 1)

    def test_on_connection_revived(self):
        """Test that connection revival resets retry counter."""
        cfg.CONF.set_override("connection_retry_max_attempts", 5, group="messaging")
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # Simulate some failed attempts
        consumer.on_connection_error(exc, 1.0)
        consumer.on_connection_error(exc, 1.0)
        consumer.on_connection_error(exc, 1.0)
        self.assertEqual(consumer._connection_retry_count, 3)

        # Connection revived should reset counter
        consumer.on_connection_revived()
        self.assertEqual(consumer._connection_retry_count, 0)

    def test_on_connection_revived_no_previous_errors(self):
        """Test that connection revival with no previous errors is safe."""
        consumer = MockConsumer()
        self.assertEqual(consumer._connection_retry_count, 0)

        # Should not raise or cause issues
        consumer.on_connection_revived()
        self.assertEqual(consumer._connection_retry_count, 0)

    @mock.patch("st2common.transport.connection_retry_mixin.LOG")
    def test_logging_on_error(self, mock_log):
        """Test that appropriate log messages are generated on connection errors."""
        cfg.CONF.set_override("connection_retry_max_attempts", 3, group="messaging")
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # First error should log warning
        consumer.on_connection_error(exc, 1.0)
        self.assertTrue(mock_log.warning.called)

        # Reset mock
        mock_log.reset_mock()

        # Error exceeding limit should log error
        consumer.on_connection_error(exc, 1.0)

        # Third call should raise and log error
        with self.assertRaises(Exception):
            consumer.on_connection_error(exc, 1.0)

        self.assertTrue(mock_log.error.called)

    @mock.patch("st2common.transport.connection_retry_mixin.LOG")
    def test_logging_on_revival(self, mock_log):
        """Test that log message is generated when connection is revived."""
        consumer = MockConsumer()

        exc = Exception("Connection failed")

        # Simulate some failures
        consumer.on_connection_error(exc, 1.0)
        consumer.on_connection_error(exc, 1.0)

        # Reset mock to check revival logging
        mock_log.reset_mock()

        # Connection revived should log info
        consumer.on_connection_revived()
        self.assertTrue(mock_log.info.called)
