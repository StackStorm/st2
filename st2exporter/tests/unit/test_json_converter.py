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

from st2tests.fixturesloader import FixturesLoader
from st2exporter.exporter.json_converter import JsonConverter

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class TestJsonConverter(unittest2.TestCase):

    fixtures_loader = FixturesLoader()
    loaded_fixtures = fixtures_loader.load_fixtures(fixtures_pack=DESCENDANTS_PACK,
                                                    fixtures_dict=DESCENDANTS_FIXTURES)

    def test_convert(self):
        executions_list = self.loaded_fixtures['executions'].values()
        converter = JsonConverter()
        converted_doc = converter.convert(executions_list)
        self.assertTrue(type(converted_doc), 'string')
        reversed_doc = json.loads(converted_doc)
        self.assertListEqual(executions_list, reversed_doc)

    def test_convert_non_list(self):
        executions_dict = self.loaded_fixtures['executions']
        converter = JsonConverter()
        try:
            converter.convert(executions_dict)
            self.fail('Should have thrown exception.')
        except ValueError:
            pass
