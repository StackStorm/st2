import unittest2

from st2common.models.system.action import (FabricRemoteAction, FabricRemoteScriptAction)


class FabricRemoteActionsTest(unittest2.TestCase):

    def test_fabric_remote_action_method(self):
        remote_action = FabricRemoteAction('foo', 'foo-id', 'ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=False)
        self.assertTrue(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(remote_action._get_action_method() == remote_action._run)
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._run)

    def test_fabric_remote_action_method_sudo(self):
        remote_action = FabricRemoteAction('foo', 'foo-id', 'ls -lrth', on_behalf_user='stan',
                                           parallel=True, sudo=True)
        self.assertTrue(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(remote_action._get_action_method() == remote_action._sudo)
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._sudo)

    def test_fabric_remote_script_action_method(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False)
        self.assertTrue(remote_action.get_on_behalf_user(), 'stan')
        fabric_task = remote_action.get_fabric_task()
        self.assertTrue(fabric_task is not None)
        self.assertTrue(fabric_task.wrapped == remote_action._run_script)

    def test_remote_dir_script_action_method_default(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False)
        self.assertTrue(remote_action.remote_dir, '/tmp')
        self.assertTrue(remote_action.remote_script, '/tmp/st2.py')

    def test_remote_dir_script_action_method_override(self):
        remote_action = FabricRemoteScriptAction('foo', 'foo-id', '/tmp/st2.py',
                                                 on_behalf_user='stan',
                                                 parallel=True, sudo=False, remote_dir='/foo')
        self.assertTrue(remote_action.remote_dir, '/foo')
        self.assertTrue(remote_action.remote_script, '/foo/st2.py')
