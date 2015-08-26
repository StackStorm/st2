import os
import sys
import unittest

import mock
from oslo_config import cfg

from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.util.sandboxing import get_sandbox_path
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
import st2tests.config as tests_config


class SandboxingUtilsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

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
        old_path = os.environ.get('PATH', '')
        os.environ['PATH'] = '/home/path1:/home/path2:/home/path3:'

        virtualenv_path = '/home/venv/test'
        result = get_sandbox_path(virtualenv_path=virtualenv_path)
        self.assertEqual(result, '/home/venv/test/bin/:/home/path1:/home/path2:/home/path3')

        os.environ['PATH'] = old_path

    @mock.patch('st2common.util.sandboxing.get_python_lib')
    def test_get_sandbox_python_path(self, mock_get_python_lib):
        # No inheritence
        python_path = get_sandbox_python_path(inherit_from_parent=False,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':')

        # Inherit python path from current process
        # Mock the current process python path
        old_python_path = os.environ.get('PYTHONPATH', '')
        os.environ['PYTHONPATH'] = ':/data/test1:/data/test2'

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (not running inside virtualenv)
        old_real_prefix = sys.real_prefix
        del sys.real_prefix

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

        os.environ['PYTHONPATH'] = old_python_path
        sys.real_prefix = old_real_prefix
