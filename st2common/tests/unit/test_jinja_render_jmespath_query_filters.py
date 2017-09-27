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


import json
import unittest2

from st2common.util import jinja as jinja_utils


class JinjaUtilsJmespathQueryTestCase(unittest2.TestCase):

    def test_jmespath_query_static(self):
        env = jinja_utils.get_jinja_environment()
        obj = {'people': [{'first': 'James', 'last': 'd'},
                          {'first': 'Jacob', 'last': 'e'},
                          {'first': 'Jayden', 'last': 'f'},
                          {'missing': 'different'}],
               'foo': {'bar': 'baz'}}

        template = '{{ obj | jmespath_query("people[*].first") }}'
        actual_str = env.from_string(template).render({'obj': obj})
        actual = eval(actual_str)
        expected = ['James', 'Jacob', 'Jayden']
        self.assertEqual(actual, expected)


    def test_jmespath_query_dynamic(self):
        env = jinja_utils.get_jinja_environment()
        obj = {'people': [{'first': 'James', 'last': 'd'},
                          {'first': 'Jacob', 'last': 'e'},
                          {'first': 'Jayden', 'last': 'f'},
                          {'missing': 'different'}],
               'foo': {'bar': 'baz'}}
        query = "people[*].last"

        template = '{{ obj | jmespath_query(query) }}'
        actual_str = env.from_string(template).render({'obj': obj,
                                                       'query': query})
        actual = eval(actual_str)
        expected = ['d', 'e', 'f']
        self.assertEqual(actual, expected)
