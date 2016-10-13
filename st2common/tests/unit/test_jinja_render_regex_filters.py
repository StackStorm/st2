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

import unittest2

from st2common.util import jinja as jinja_utils


class JinjaUtilsRegexFilterTestCase(unittest2.TestCase):

    def test_filters_regex_match(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{k1 | regex_match("x")}}'
        actual = env.from_string(template).render({'k1': 'xyz'})
        expected = 'True'
        self.assertEqual(actual, expected)

        template = '{{k1 | regex_match("y")}}'
        actual = env.from_string(template).render({'k1': 'xyz'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{k1 | regex_match("^v(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)$")}}'
        actual = env.from_string(template).render({'k1': 'v0.10.1'})
        expected = 'True'
        self.assertEqual(actual, expected)

    def test_filters_regex_replace(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{k1 | regex_replace("x", "y")}}'
        actual = env.from_string(template).render({'k1': 'xyz'})
        expected = 'yyz'
        self.assertEqual(actual, expected)

        template = '{{k1 | regex_replace("(blue|white|red)", "color")}}'
        actual = env.from_string(template).render({'k1': 'blue socks and red shoes'})
        expected = 'color socks and color shoes'
        self.assertEqual(actual, expected)

    def test_filters_regex_search(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{k1 | regex_search("x")}}'
        actual = env.from_string(template).render({'k1': 'xyz'})
        expected = 'True'
        self.assertEqual(actual, expected)

        template = '{{k1 | regex_search("y")}}'
        actual = env.from_string(template).render({'k1': 'xyz'})
        expected = 'True'
        self.assertEqual(actual, expected)

        template = '{{k1 | regex_search("^v(\\d+\\.)?(\\d+\\.)?(\\*|\\d+)$")}}'
        actual = env.from_string(template).render({'k1': 'v0.10.1'})
        expected = 'True'
        self.assertEqual(actual, expected)
