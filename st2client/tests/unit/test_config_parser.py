# coding=utf-8
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

from __future__ import absolute_import
import os
import shutil

import mock
import six
import unittest2

from st2client.config_parser import CLIConfigParser
from st2client.config_parser import CONFIG_DEFAULT_VALUES

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH_FULL = os.path.join(BASE_DIR, '../fixtures/st2rc.full.ini')
CONFIG_FILE_PATH_PARTIAL = os.path.join(BASE_DIR, '../fixtures/st2rc.partial.ini')
CONFIG_FILE_PATH_UNICODE = os.path.join(BASE_DIR, '../fixtures/test_unicode.ini')


class CLIConfigParserTestCase(unittest2.TestCase):
    def test_constructor(self):
        parser = CLIConfigParser(config_file_path='doesnotexist', validate_config_exists=False)
        self.assertTrue(parser)

        self.assertRaises(ValueError, CLIConfigParser, config_file_path='doestnotexist',
                          validate_config_exists=True)

    def test_correct_permissions_emit_no_warnings(self):
        TEMP_FILE_PATH = os.path.join('st2config', '.st2', 'config')
        TEMP_CONFIG_DIR = os.path.dirname(TEMP_FILE_PATH)

        if os.path.exists(TEMP_FILE_PATH):
            os.remove(TEMP_FILE_PATH)
        self.assertFalse(os.path.exists(TEMP_FILE_PATH))

        if os.path.exists(TEMP_CONFIG_DIR):
            os.removedirs(TEMP_CONFIG_DIR)
        self.assertFalse(os.path.exists(TEMP_CONFIG_DIR))

        try:
            # Setup the config directory
            os.makedirs(TEMP_CONFIG_DIR)
            os.chmod(TEMP_CONFIG_DIR, 0o2770)

            self.assertEqual(os.stat(TEMP_CONFIG_DIR).st_mode & 0o7777, 0o2770)

            # Setup the config file
            shutil.copyfile(CONFIG_FILE_PATH_FULL, TEMP_FILE_PATH)
            os.chmod(TEMP_FILE_PATH, 0o660)

            self.assertEqual(os.stat(TEMP_FILE_PATH).st_mode & 0o777, 0o660)

            parser = CLIConfigParser(config_file_path=TEMP_FILE_PATH, validate_config_exists=True)
            parser.LOG = mock.Mock()

            result = parser.parse()  # noqa F841

            self.assertEqual(parser.LOG.warn.call_count, 0)

            # Make sure we left the file alone
            self.assertTrue(os.path.exists(TEMP_FILE_PATH))
            self.assertEqual(os.stat(TEMP_FILE_PATH).st_mode & 0o777, 0o660)

            self.assertTrue(os.path.exists(TEMP_CONFIG_DIR))
            self.assertEqual(os.stat(TEMP_CONFIG_DIR).st_mode & 0o7777, 0o2770)
        finally:
            if os.path.exists(TEMP_FILE_PATH):
                os.remove(TEMP_FILE_PATH)
                self.assertFalse(os.path.exists(TEMP_FILE_PATH))

            if os.path.exists(TEMP_CONFIG_DIR):
                os.removedirs(TEMP_CONFIG_DIR)
                self.assertFalse(os.path.exists(TEMP_FILE_PATH))

    def test_warn_on_bad_config_permissions(self):
        TEMP_FILE_PATH = os.path.join('st2config', '.st2', 'config')
        TEMP_CONFIG_DIR = os.path.dirname(TEMP_FILE_PATH)

        if os.path.exists(TEMP_FILE_PATH):
            os.remove(TEMP_FILE_PATH)
        self.assertFalse(os.path.exists(TEMP_FILE_PATH))

        if os.path.exists(TEMP_CONFIG_DIR):
            os.removedirs(TEMP_CONFIG_DIR)
        self.assertFalse(os.path.exists(TEMP_CONFIG_DIR))

        try:
            # Setup the config directory
            os.makedirs(TEMP_CONFIG_DIR)
            os.chmod(TEMP_CONFIG_DIR, 0o0755)

            self.assertNotEqual(os.stat(TEMP_CONFIG_DIR).st_mode & 0o7777, 0o0770)

            # Setup the config file
            shutil.copyfile(CONFIG_FILE_PATH_FULL, TEMP_FILE_PATH)
            os.chmod(TEMP_FILE_PATH, 0o664)

            self.assertNotEqual(os.stat(TEMP_FILE_PATH).st_mode & 0o777, 0o770)

            parser = CLIConfigParser(config_file_path=TEMP_FILE_PATH, validate_config_exists=True)
            parser.LOG = mock.Mock()

            result = parser.parse()  # noqa F841

            self.assertEqual(parser.LOG.info.call_count, 1)

            self.assertEqual(
                "The SGID bit is not set on the StackStorm configuration directory."
                "\n\n"
                "You can fix this by running:"
                "\n\n"
                "chmod g+s {config_dir}".format(config_dir=TEMP_CONFIG_DIR),
                parser.LOG.info.call_args_list[0][0][0])

            self.assertEqual(parser.LOG.warn.call_count, 2)
            self.assertEqual(
                "The StackStorm configuration directory permissions are insecure "
                "(too permissive)."
                "\n\n"
                "You can fix this by running:"
                "\n\n"
                "chmod 770 {config_dir}".format(config_dir=TEMP_CONFIG_DIR),
                parser.LOG.warn.call_args_list[0][0][0])

            self.assertEqual(
                "The StackStorm configuration file permissions are insecure."
                "\n\n"
                "You can fix this by running:"
                "\n\n"
                "chmod 660 {config_file}".format(config_file=TEMP_FILE_PATH),
                parser.LOG.warn.call_args_list[1][0][0])

            # Make sure we left the file alone
            self.assertTrue(os.path.exists(TEMP_FILE_PATH))
            self.assertEqual(os.stat(TEMP_FILE_PATH).st_mode & 0o777, 0o664)

            self.assertTrue(os.path.exists(TEMP_CONFIG_DIR))
            self.assertEqual(os.stat(TEMP_CONFIG_DIR).st_mode & 0o7777, 0o0755)
        finally:
            if os.path.exists(TEMP_FILE_PATH):
                os.remove(TEMP_FILE_PATH)
                self.assertFalse(os.path.exists(TEMP_FILE_PATH))

            if os.path.exists(TEMP_CONFIG_DIR):
                os.removedirs(TEMP_CONFIG_DIR)
                self.assertFalse(os.path.exists(TEMP_FILE_PATH))

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
            },
            'stream': {
                'url': 'http://127.0.0.1:9102/v1/stream'
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

    def test_get_config_for_unicode_char(self):
        parser = CLIConfigParser(config_file_path=CONFIG_FILE_PATH_UNICODE,
                                 validate_config_exists=False)
        config = parser.parse()

        if six.PY3:
            self.assertEqual(config['credentials']['password'], '密码')
        else:
            self.assertEqual(config['credentials']['password'], u'\u5bc6\u7801')
