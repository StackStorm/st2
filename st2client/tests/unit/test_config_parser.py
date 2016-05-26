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

import os

import unittest2

from st2client.config_parser import CLIConfigParser
from st2client.config_parser import CONFIG_DEFAULT_VALUES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH_FULL = os.path.join(BASE_DIR, '../fixtures/st2rc.full.ini')
CONFIG_FILE_PATH_PARTIAL = os.path.join(BASE_DIR, '../fixtures/st2rc.partial.ini')


class CLIConfigParserTestCase(unittest2.TestCase):
    def test_constructor(self):
        parser = CLIConfigParser(config_file_path='doesnotexist', validate_config_exists=False)
        self.assertTrue(parser)

        self.assertRaises(ValueError, CLIConfigParser, config_file_path='doestnotexist',
                          validate_config_exists=True)

    def test_parse(self):
        # File doesn't exist
        parser = CLIConfigParser(config_file_path='doesnotexist', validate_config_exists=False)
        result = parser.parse()

        self.assertEqual(CONFIG_DEFAULT_VALUES, result)

        # File exists - all the options specified
        expected = {
            'general': {
                'base_url': 'http://127.0.0.1',
                'api_version': 'v1',
                'cacert': 'cacartpath',
                'silence_ssl_warnings': False
            },
            'cli': {
                'debug': True,
                'cache_token': False,
                'timezone': 'UTC'
            },
            'credentials': {
                'username': 'test1',
                'password': 'test1',
                'api_key': None
            },
            'api': {
                'url': 'http://127.0.0.1:9101/v1'
            },
            'auth': {
                'url': 'http://127.0.0.1:9100/'
            }
        }
        parser = CLIConfigParser(config_file_path=CONFIG_FILE_PATH_FULL,
                                 validate_config_exists=False)
        result = parser.parse()
        self.assertEqual(expected, result)

        # File exists - missing options, test defaults
        parser = CLIConfigParser(config_file_path=CONFIG_FILE_PATH_PARTIAL,
                                 validate_config_exists=False)
        result = parser.parse()
        self.assertTrue(result['cli']['cache_token'], True)
