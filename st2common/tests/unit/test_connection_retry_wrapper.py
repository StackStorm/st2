# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest

from st2common.transport.connection_retry_wrapper import ClusterRetryContext


class TestClusterRetryContext(unittest.TestCase):

    def test_single_node_cluster_retry(self):
        retry_context = ClusterRetryContext(cluster_size=1)
        should_stop, wait = retry_context.test_should_stop()
        self.assertFalse(should_stop, 'Not done trying.')
        self.assertEqual(wait, 10)

        should_stop, wait = retry_context.test_should_stop()
        self.assertFalse(should_stop, 'Not done trying.')
        self.assertEqual(wait, 10)

        should_stop, wait = retry_context.test_should_stop()
        self.assertTrue(should_stop, 'Done trying.')
        self.assertEqual(wait, -1)

    def test_multiple_node_cluster_retry(self):
        cluster_size = 3
        last_index = cluster_size * 2

        retry_context = ClusterRetryContext(cluster_size=cluster_size)

        for i in range(last_index + 1):
            should_stop, wait = retry_context.test_should_stop()
            if i == last_index:
                self.assertTrue(should_stop, 'Done trying.')
                self.assertEqual(wait, -1)
            else:
                self.assertFalse(should_stop, 'Not done trying.')
                # on cluster boundaries the wait is longer. Short wait when switching
                # to a different server within a cluster.
                if (i +1) % cluster_size == 0:
                    self.assertEqual(wait, 10)
                else:
                    self.assertEqual(wait, 0)

    def test_zero_node_cluster_retry(self):
        retry_context = ClusterRetryContext(cluster_size=0)
        should_stop, wait = retry_context.test_should_stop()
        self.assertTrue(should_stop, 'Done trying.')
        self.assertEqual(wait, -1)
