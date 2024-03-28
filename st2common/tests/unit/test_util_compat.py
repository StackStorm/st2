# -*- coding: utf-8 -*-
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

from st2common.util.compat import to_ascii

__all__ = ["CompatUtilsTestCase"]


class CompatUtilsTestCase(unittest.TestCase):
    def test_to_ascii(self):
        expected_values = [
            ("already ascii", "already ascii"),
            ("foo", "foo"),
            ("٩(̾●̮̮̃̾•̃̾)۶", "()"),
            ("\xd9\xa9", ""),
        ]

        for input_value, expected_value in expected_values:
            result = to_ascii(input_value)
            self.assertEqual(result, expected_value)
