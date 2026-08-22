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
Tests for QueueConsumer connection retry behavior.
"""

from __future__ import absolute_import
import unittest
from unittest.mock import Mock

from oslo_config import cfg

from st2common.transport.consumers import QueueConsumer


class TestConsumerRetryLimits(unittest.TestCase):
    """Test QueueConsumer respects connection retry limits"""

    def setUp(self):
        """Reset config before each test"""
        super(TestConsumerRetryLimits, self).setUp()
        # Clear any config overrides from previous tests
        try:
            cfg.CONF.clear_override("connection_retry_max_attempts", group="messaging")
        except:
            pass

    def test_on_connection_error_raises_after_max_retries(self):
        """Test that on_connection_error raises exception after max retries"""
        cfg.CONF.set_override("connection_retry_max_attempts", 3, group="messaging")

        mock_connection = Mock()
        mock_queues = []
        mock_handler = Mock()

        consumer = QueueConsumer(mock_connection, mock_queues, mock_handler)

        test_exc = ConnectionRefusedError(111, "ECONNREFUSED")

        # First 2 attempts should not raise
        consumer.on_connection_error(test_exc, 1.0)
        self.assertEqual(consumer._connection_retry_count, 1)

        consumer.on_connection_error(test_exc, 2.0)
        self.assertEqual(consumer._connection_retry_count, 2)

        # 3rd attempt should raise
        with self.assertRaises(ConnectionRefusedError):
            consumer.on_connection_error(test_exc, 4.0)

        self.assertEqual(consumer._connection_retry_count, 3)

    def test_on_connection_revived_resets_counter(self):
        """Test that on_connection_revived resets the retry counter"""
        cfg.CONF.set_override("connection_retry_max_attempts", 5, group="messaging")

        mock_connection = Mock()
        mock_queues = []
        mock_handler = Mock()

        consumer = QueueConsumer(mock_connection, mock_queues, mock_handler)

        test_exc = ConnectionRefusedError(111, "ECONNREFUSED")

        # Fail twice
        consumer.on_connection_error(test_exc, 1.0)
        consumer.on_connection_error(test_exc, 2.0)
        self.assertEqual(consumer._connection_retry_count, 2)

        # Connection revived
        consumer.on_connection_revived()
        self.assertEqual(consumer._connection_retry_count, 0)

        # Can retry again from 0
        consumer.on_connection_error(test_exc, 1.0)
        self.assertEqual(consumer._connection_retry_count, 1)

    def test_zero_max_retries_allows_infinite_retries(self):
        """Test that setting max_retries to 0 allows infinite retries"""
        cfg.CONF.set_override("connection_retry_max_attempts", 0, group="messaging")

        mock_connection = Mock()
        mock_queues = []
        mock_handler = Mock()

        consumer = QueueConsumer(mock_connection, mock_queues, mock_handler)

        test_exc = ConnectionRefusedError(111, "ECONNREFUSED")

        # Should be able to retry many times without raising
        for i in range(100):
            consumer.on_connection_error(test_exc, 1.0)
            self.assertEqual(consumer._connection_retry_count, i + 1)
