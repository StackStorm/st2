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
import re

from unittest import TestCase

import st2common.util.queues as queue_utils


class TestQueueUtils(TestCase):
    def test_get_queue_name(self):
        self.assertRaises(
            ValueError,
            queue_utils.get_queue_name,
            queue_name_base=None,
            queue_name_suffix=None,
        )
        self.assertRaises(
            ValueError,
            queue_utils.get_queue_name,
            queue_name_base="",
            queue_name_suffix=None,
        )
        self.assertEqual(
            queue_utils.get_queue_name(
                queue_name_base="st2.test.watch", queue_name_suffix=None
            ),
            "st2.test.watch",
        )
        self.assertEqual(
            queue_utils.get_queue_name(
                queue_name_base="st2.test.watch", queue_name_suffix=""
            ),
            "st2.test.watch",
        )
        queue_name = queue_utils.get_queue_name(
            queue_name_base="st2.test.watch",
            queue_name_suffix="foo",
            add_random_uuid_to_suffix=True,
        )
        pattern = re.compile(r"st2.test.watch.foo-\w")
        self.assertTrue(re.match(pattern, queue_name))

        queue_name = queue_utils.get_queue_name(
            queue_name_base="st2.test.watch",
            queue_name_suffix="foo",
            add_random_uuid_to_suffix=False,
        )
        self.assertEqual(queue_name, "st2.test.watch.foo")
