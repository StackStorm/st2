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

import unittest2
import mock

from st2client.utils.terminal import DEFAULT_TERMINAL_SIZE_LINES
from st2client.utils.terminal import DEFAULT_TERMINAL_SIZE_COLUMNS
from st2client.utils.terminal import get_terminal_size

__all__ = [
    'TerminalUtilsTestCase'
]


class TerminalUtilsTestCase(unittest2.TestCase):
    @mock.patch.dict(os.environ, {'LINES': '111', 'COLUMNS': '222'})
    def test_get_terminal_size_lines_columns_environment_variable_have_precedence(self):
        # Verify that LINES and COLUMNS environment variables have precedence over other approaches
        lines, columns = get_terminal_size()

        self.assertEqual(lines, 111)
        self.assertEqual(columns, 222)

    @mock.patch('struct.unpack', mock.Mock(side_effect=Exception('a')))
    @mock.patch('subprocess.Popen')
    def test_get_terminal_size_subprocess_popen_is_used(self, mock_popen):
        mock_communicate = mock.Mock(return_value=['555 666'])

        mock_process = mock.Mock()
        mock_process.returncode = 0
        mock_process.communicate = mock_communicate

        mock_popen.return_value = mock_process

        lines, columns = get_terminal_size()
        self.assertEqual(lines, 555)
        self.assertEqual(columns, 666)

    @mock.patch('struct.unpack', mock.Mock(side_effect=Exception('a')))
    @mock.patch('subprocess.Popen', mock.Mock(side_effect=Exception('b')))
    def test_get_terminal_size_default_values_are_used(self):
        lines, columns = get_terminal_size()

        self.assertEqual(lines, DEFAULT_TERMINAL_SIZE_LINES)
        self.assertEqual(columns, DEFAULT_TERMINAL_SIZE_COLUMNS)
