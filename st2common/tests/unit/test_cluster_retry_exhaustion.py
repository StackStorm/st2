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
Test to verify ClusterRetryContext stops retrying after max attempts.
"""

from __future__ import absolute_import
import unittest

from st2common.transport.connection_retry_wrapper import ClusterRetryContext


class TestClusterRetryExhaustion(unittest.TestCase):
    """Test that ClusterRetryContext respects max_retries"""

    def test_should_stop_returns_true_after_max_retries(self):
        """Test that should_stop returns True after max_retries exhausted"""
        context = ClusterRetryContext(cluster_size=2, max_retries=2)

        # Simulate failures on all nodes, cycling through the cluster
        test_exc = Exception("Connection failed")

        # cluster_size=2, max_retries=2 means: 2 * (2+1) = 6 total attempts
        # First cycle through cluster (2 nodes)
        should_stop, wait = context.should_stop(test_exc)
        self.assertFalse(should_stop)  # Node 1, attempt 1

        should_stop, wait = context.should_stop(test_exc)
        self.assertFalse(should_stop)  # Node 2, attempt 1

        # Second cycle through cluster (2 nodes)
        should_stop, wait = context.should_stop(test_exc)
        self.assertFalse(should_stop)  # Node 1, attempt 2

        should_stop, wait = context.should_stop(test_exc)
        self.assertFalse(should_stop)  # Node 2, attempt 2

        # Third cycle through cluster (2 nodes)
        should_stop, wait = context.should_stop(test_exc)
        self.assertFalse(should_stop)  # Node 1, attempt 3

        should_stop, wait = context.should_stop(test_exc)
        self.assertTrue(should_stop)  # Node 2, attempt 3 - should stop here

    def test_should_stop_stops_at_exact_max_retries(self):
        """Test that max_retries is respected exactly"""
        context = ClusterRetryContext(cluster_size=3, max_retries=1)

        test_exc = Exception("Connection failed")

        # cluster_size=3, max_retries=1 means: 3 * (1+1) = 6 total attempts
        for i in range(5):
            should_stop, wait = context.should_stop(test_exc)
            self.assertFalse(should_stop, f"Should not stop at attempt {i+1}")

        # 6th attempt should stop
        should_stop, wait = context.should_stop(test_exc)
        self.assertTrue(should_stop, "Should stop after 6 attempts")
