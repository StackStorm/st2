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

import unittest

from st2common.util.types import OrderedSet

__all__ = ["OrderedTestTypeTestCase"]


class OrderedTestTypeTestCase(unittest.TestCase):
    def test_ordered_set(self):
        set1 = OrderedSet([1, 2, 3, 3, 4, 2, 1, 5])
        self.assertEqual(set1, [1, 2, 3, 4, 5])

        set2 = OrderedSet([5, 4, 3, 2, 1])
        self.assertEqual(set2, [5, 4, 3, 2, 1])

        set3 = OrderedSet([1, 2, 3, 4, 5, 5, 4, 3, 2, 1])
        self.assertEqual(set3, [1, 2, 3, 4, 5])

        set4 = OrderedSet([1, 1, 1, 1, 4, 4, 4, 9])
        self.assertEqual(set4, [1, 4, 9])
