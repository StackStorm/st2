# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
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
import sys
import unittest

import mock
from oslo_config import cfg

from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.util.sandboxing import get_sandbox_path
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_path_for_python_action
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import clear_virtualenv_prefix
from st2common.util.sandboxing import get_virtualenv_prefix
from st2common.util.sandboxing import set_virtualenv_prefix

import st2tests.config as tests_config

__all__ = [
    'SandboxingUtilsTestCase'
]


class SandboxingUtilsTestCase(unittest.TestCase):
    def setUp(self):
        super(SandboxingUtilsTestCase, self).setUp()

        # Restore PATH and other variables before each test case
        os.environ['PATH'] = self.old_path
        os.environ['PYTHONPATH'] = self.old_python_path
        set_virtualenv_prefix(self.old_virtualenv_prefix)

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

        # Store original values so we can restore them in setUp
        cls.old_path = os.environ.get('PATH', '')
        cls.old_python_path = os.environ.get('PYTHONPATH', '')
        cls.old_virtualenv_prefix = get_virtualenv_prefix()

    @classmethod
    def tearDownClass(cls):
        os.environ['PATH'] = cls.old_path
        os.environ['PYTHONPATH'] = cls.old_python_path
        set_virtualenv_prefix(cls.old_virtualenv_prefix)

    def test_get_sandbox_python_binary_path(self):
        # Non-system content pack, should use pack specific virtualenv binary
        result = get_sandbox_python_binary_path(pack='mapack')
        expected = os.path.join(cfg.CONF.system.base_path, 'virtualenvs/mapack/bin/python')
        self.assertEqual(result, expected)

        # System content pack, should use current process (system) python binary
        result = get_sandbox_python_binary_path(pack=SYSTEM_PACK_NAMES[0])
        self.assertEqual(result, sys.executable)

    def test_get_sandbox_path(self):
        # Mock the current PATH value
        os.environ['PATH'] = '/home/path1:/home/path2:/home/path3:'

        virtualenv_path = '/home/venv/test'
        result = get_sandbox_path(virtualenv_path=virtualenv_path)
        self.assertEqual(result, '/home/venv/test/bin/:/home/path1:/home/path2:/home/path3')

    @mock.patch('st2common.util.sandboxing.get_python_lib')
    def test_get_sandbox_python_path(self, mock_get_python_lib):
        # No inheritance
        python_path = get_sandbox_python_path(inherit_from_parent=False,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':')

        # Inherit python path from current process
        # Mock the current process python path
        os.environ['PYTHONPATH'] = ':/data/test1:/data/test2'

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (not running inside virtualenv)
        clear_virtualenv_prefix()

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (running inside virtualenv)
        sys.real_prefix = '/usr'
        mock_get_python_lib.return_value = sys.prefix + '/virtualenvtest'
        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=True)
        self.assertEqual(python_path, ':/data/test1:/data/test2:%s/virtualenvtest' %
                         (sys.prefix))

    @mock.patch('os.path.isdir', mock.Mock(return_value=True))
    @mock.patch('os.listdir', mock.Mock(return_value=['python2.7']))
    @mock.patch('st2common.util.sandboxing.get_python_lib')
    def test_get_sandbox_python_path_for_python_action_python2_used_for_venv(self,
            mock_get_python_lib):

        # No inheritance
        python_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=False,
                                                                inherit_parent_virtualenv=False)

        actual = python_path.strip(':').split(':')
        self.assertEqual(len(actual), 3)

        self.assertEqual(actual, [
            # First entry should be lib/python3 dir from venv
            'virtualenvs/dummy_pack/lib/python3.6',
            # Second entry should be python3 site-packages dir from venv
            'virtualenvs/dummy_pack/lib/python3.6/site-packages',
            # Third entry should be actions/lib dir from pack root directory
            'packs/dummy_pack/actions/lib',
        ])

        # Inherit python path from current process
        # Mock the current process python path
        os.environ['PYTHONPATH'] = ':/data/test1:/data/test2'

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        actual_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=True,
                                                                inherit_parent_virtualenv=False)
        self.assertEqual(actual_path, [
            # First entry should be lib/python3 dir from venv
            '/tmp/virtualenvs/dummy_pack/lib/python3.6',
            # Second entry should be python3 site-packages dir from venv
            '/tmp/virtualenvs/dummy_pack/lib/python3.6/site-packages',
            # Third entry should be actions/lib dir from pack root directory
            '/tmp/packs/dummy_pack/actions/lib',
            # And the rest of the paths from get_sandbox_python_path
            '',
            '/data/test1',
            '/data/test2',
        ])

        # Inherit from current process and from virtualenv (not running inside virtualenv)
        clear_virtualenv_prefix()

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        actual_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=True,
                                                                inherit_parent_virtualenv=True)

        self.assertEqual(actual_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (running inside virtualenv)
        sys.real_prefix = '/usr'
        mock_get_python_lib.return_value = f'{sys.prefix}virtualenvtest'
        actual_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=True,
                                                                inherit_parent_virtualenv=True)

        self.assertEqual(actual_path, [
            '/tmp/virtualenvs/dummy_pack/lib/python3.6',
            '/tmp/virtualenvs/dummy_pack/lib/python3.6/site-packages',
            '/tmp/packs/dummy_pack/actions/lib',
            '',
            '/data/test1',
            '/data/test2',
            f'{sys.prefix}/virtualenvtest',
        ])
