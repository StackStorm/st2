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

from unittest2 import TestCase

from st2common.util.config_parser import ContentPackConfigParser
import st2tests.config as tests_config


class ContentPackConfigParserTestCase(TestCase):
    def setUp(self):
        super(ContentPackConfigParserTestCase, self).setUp()
        tests_config.parse_args()

    def test_get_config_inexistent_pack(self):
        parser = ContentPackConfigParser(pack_name='inexistent')
        config = parser.get_config()
        self.assertEqual(config, None)

    def test_get_config_no_config(self):
        pack_name = 'dummy_pack_1'
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_config()
        self.assertEqual(config, None)

    def test_get_config_existing_config(self):
        pack_name = 'dummy_pack_2'
        parser = ContentPackConfigParser(pack_name=pack_name)

        config = parser.get_config()
        self.assertEqual(config.config['section1']['key1'], 'value1')
        self.assertEqual(config.config['section2']['key10'], 'value10')
