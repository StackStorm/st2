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
import getpass

import unittest2
import mock

from st2client.base import BaseCLIApp

USER = getpass.getuser()


class BaseCLIAppTestCase(unittest2.TestCase):
    @mock.patch('os.path.isfile', mock.Mock())
    def test_cli_config_file_path(self):
        app = BaseCLIApp()
        args = mock.Mock()

        # 1. Absolute path
        args.config_file = '/tmp/full/abs/path/config.ini'
        result = app._get_config_file_path(args=args)
        self.assertEqual(result, args.config_file)

        args.config_file = '/home/user/st2/config.ini'
        result = app._get_config_file_path(args=args)
        self.assertEqual(result, args.config_file)

        # 2. Path relative to user home directory, should get expanded
        args.config_file = '~/.st2/config.ini'
        result = app._get_config_file_path(args=args)
        expected = os.path.join(os.path.expanduser('~' + USER), '.st2/config.ini')
        self.assertEqual(result, expected)

        # 3. Relative path (should get converted to absolute one)
        args.config_file = 'config.ini'
        result = app._get_config_file_path(args=args)
        expected = os.path.join(os.getcwd(), 'config.ini')
        self.assertEqual(result, expected)

        args.config_file = '.st2/config.ini'
        result = app._get_config_file_path(args=args)
        expected = os.path.join(os.getcwd(), '.st2/config.ini')
        self.assertEqual(result, expected)
