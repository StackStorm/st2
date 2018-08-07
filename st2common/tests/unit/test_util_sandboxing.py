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
        sys.real_prefix = self.old_real_prefix

    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

        # Store original values so we can restore them in setUp
        cls.old_path = os.environ.get('PATH', '')
        cls.old_python_path = os.environ.get('PYTHONPATH', '')
        cls.old_real_prefix = sys.real_prefix

    @classmethod
    def tearDownClass(cls):
        os.environ['PATH'] = cls.old_path
        os.environ['PYTHONPATH'] = cls.old_python_path
        sys.real_prefix = cls.old_real_prefix

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

    @mock.patch('os.path.isdir', mock.Mock(return_value=True))
    @mock.patch('os.listdir', mock.Mock(return_value=['python2.7']))
    @mock.patch('st2common.util.sandboxing.get_python_lib')
    def test_get_sandbox_python_path_for_python_action_python2_used_for_venv(self,
            mock_get_python_lib):
        # No inheritance
        python_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=False,
                                                                inherit_parent_virtualenv=False)

        self.assertEqual(python_path, ':')

        # Inherit python path from current process
        # Mock the current process python path
        os.environ['PYTHONPATH'] = ':/data/test1:/data/test2'

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (not running inside virtualenv)
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

    @mock.patch('os.path.isdir', mock.Mock(return_value=True))
    @mock.patch('os.listdir', mock.Mock(return_value=['python3.6']))
    @mock.patch('st2common.util.sandboxing.get_python_lib')
    @mock.patch('st2common.util.sandboxing.get_pack_base_path',
                mock.Mock(return_value='/tmp/packs/dummy_pack'))
    @mock.patch('st2common.util.sandboxing.get_sandbox_virtualenv_path',
                mock.Mock(return_value='/tmp/virtualenvs/dummy_pack'))
    def test_get_sandbox_python_path_for_python_action_python3_used_for_venv(self,
            mock_get_python_lib):
        # No inheritance
        python_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=False,
                                                                inherit_parent_virtualenv=False)

        split = python_path.strip(':').split(':')
        self.assertEqual(len(split), 3)

        # First entry should be lib/python3 dir from venv
        self.assertTrue('virtualenvs/dummy_pack/lib/python3.6' in split[0])

        # Second entry should be python3 site-packages dir from venv
        self.assertTrue('virtualenvs/dummy_pack/lib/python3.6/site-packages' in split[1])

        # Third entry should be actions/lib dir from pack root directory
        self.assertTrue('packs/dummy_pack/actions/lib/' in split[2])

        # Inherit python path from current process
        # Mock the current process python path
        os.environ['PYTHONPATH'] = ':/data/test1:/data/test2'

        python_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=True,
                                                                inherit_parent_virtualenv=False)
        expected = ('/tmp/virtualenvs/dummy_pack/lib/python3.6:'
                    '/tmp/virtualenvs/dummy_pack/lib/python3.6/site-packages:'
                    '/tmp/packs/dummy_pack/actions/lib/::/data/test1:/data/test2')
        self.assertEqual(python_path, expected)

        # Inherit from current process and from virtualenv (not running inside virtualenv)
        del sys.real_prefix

        python_path = get_sandbox_python_path(inherit_from_parent=True,
                                              inherit_parent_virtualenv=False)
        self.assertEqual(python_path, ':/data/test1:/data/test2')

        # Inherit from current process and from virtualenv (running inside virtualenv)
        sys.real_prefix = '/usr'
        mock_get_python_lib.return_value = sys.prefix + '/virtualenvtest'
        python_path = get_sandbox_python_path_for_python_action(pack='dummy_pack',
                                                                inherit_from_parent=True,
                                                                inherit_parent_virtualenv=True)

        expected = ('/tmp/virtualenvs/dummy_pack/lib/python3.6:'
                    '/tmp/virtualenvs/dummy_pack/lib/python3.6/site-packages:'
                    '/tmp/packs/dummy_pack/actions/lib/::/data/test1:/data/test2:'
                    '%s/virtualenvtest' % (sys.prefix))
        self.assertEqual(python_path, expected)
