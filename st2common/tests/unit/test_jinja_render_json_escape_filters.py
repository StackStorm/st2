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


class JinjaUtilsJsonEscapeTestCase(unittest2.TestCase):

    def test_doublequotes(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo """ bar'})
        expected = 'foo \\"\\"\\" bar'
        self.assertEqual(actual, expected)

    def test_backslashes(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \ bar'})
        expected = 'foo \\\\ bar'
        self.assertEqual(actual, expected)

    def test_backspace(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \b bar'})
        expected = 'foo \\b bar'
        self.assertEqual(actual, expected)

    def test_formfeed(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \f bar'})
        expected = 'foo \\f bar'
        self.assertEqual(actual, expected)

    def test_newline(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \n bar'})
        expected = 'foo \\n bar'
        self.assertEqual(actual, expected)

    def test_carriagereturn(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \r bar'})
        expected = 'foo \\r bar'
        self.assertEqual(actual, expected)

    def test_tab(self):
        env = jinja_utils.get_jinja_environment()
        template = '{{ test_str | json_escape }}'
        actual = env.from_string(template).render({'test_str': 'foo \t bar'})
        expected = 'foo \\t bar'
        self.assertEqual(actual, expected)
