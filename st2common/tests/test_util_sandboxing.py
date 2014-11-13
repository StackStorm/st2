import os
import sys
import unittest

import mock

from st2common.util.sandboxing import get_sandbox_python_path


class SandboxingUtilsTestCase(unittest.TestCase):

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
