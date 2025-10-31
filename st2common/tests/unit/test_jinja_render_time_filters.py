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

from st2common.util import jinja as jinja_utils


class JinjaUtilsTimeFilterTestCase(unittest.TestCase):
    def test_to_human_time_filter(self):
        env = jinja_utils.get_jinja_environment()

        template = "{{k1 | to_human_time_from_seconds}}"
        actual = env.from_string(template).render({"k1": 12345})
        self.assertEqual(actual, "3h25m45s")

        actual = env.from_string(template).render({"k1": 0})
        self.assertEqual(actual, "0s")

        self.assertRaises(
            AssertionError, env.from_string(template).render, {"k1": "stuff"}
        )
