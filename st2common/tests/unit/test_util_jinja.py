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
