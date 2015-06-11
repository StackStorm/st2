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


class JinjaUtilsRenderTestCase(unittest2.TestCase):

    def test_render_values(self):
        actual = jinja_utils.render_values(
            mapping={'k1': '{{a}}', 'k2': '{{b}}'},
            context={'a': 'v1', 'b': 'v2'})
        expected = {'k2': 'v2', 'k1': 'v1'}
        self.assertEqual(actual, expected)

    def test_render_values_skip_missing(self):
        actual = jinja_utils.render_values(
            mapping={'k1': '{{a}}', 'k2': '{{b}}', 'k3': '{{c}}'},
            context={'a': 'v1', 'b': 'v2'},
            allow_undefined=True)
        expected = {'k2': 'v2', 'k1': 'v1', 'k3': ''}
        self.assertEqual(actual, expected)


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


class JinjaUtilsVersionsFilterTestCase(unittest2.TestCase):

    def test_version_compare(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_compare("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.9.0'})
        expected = '-1'
        self.assertEqual(actual, expected)

        template = '{{version | version_compare("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = '1'
        self.assertEqual(actual, expected)

        template = '{{version | version_compare("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.0'})
        expected = '0'
        self.assertEqual(actual, expected)

    def test_version_more_than(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_more_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.9.0'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_more_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = 'True'
        self.assertEqual(actual, expected)

        template = '{{version | version_more_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.0'})
        expected = 'False'
        self.assertEqual(actual, expected)

    def test_version_less_than(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_less_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.9.0'})
        expected = 'True'
        self.assertEqual(actual, expected)

        template = '{{version | version_less_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_less_than("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.0'})
        expected = 'False'
        self.assertEqual(actual, expected)

    def test_version_equal(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_equal("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.9.0'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_equal("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_equal("0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.0'})
        expected = 'True'
        self.assertEqual(actual, expected)

    def test_version_match(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_match(">0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = 'True'
        self.assertEqual(actual, expected)
        actual = env.from_string(template).render({'version': '0.1.1'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_match("<0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.1.0'})
        expected = 'True'
        self.assertEqual(actual, expected)
        actual = env.from_string(template).render({'version': '1.1.0'})
        expected = 'False'
        self.assertEqual(actual, expected)

        template = '{{version | version_match("==0.10.0")}}'
        actual = env.from_string(template).render({'version': '0.10.0'})
        expected = 'True'
        self.assertEqual(actual, expected)
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = 'False'
        self.assertEqual(actual, expected)

    def test_version_bump_major(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_bump_major}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = '1.0.0'
        self.assertEqual(actual, expected)

    def test_version_bump_minor(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_bump_minor}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = '0.11.0'
        self.assertEqual(actual, expected)

    def test_version_bump_patch(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_bump_patch}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = '0.10.2'
        self.assertEqual(actual, expected)

    def test_version_strip_patch(self):
        env = jinja_utils.get_jinja_environment()

        template = '{{version | version_strip_patch}}'
        actual = env.from_string(template).render({'version': '0.10.1'})
        expected = '0.10'
        self.assertEqual(actual, expected)
