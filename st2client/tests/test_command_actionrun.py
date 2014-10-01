import unittest2

from st2client.commands.action import ActionRunCommand
from st2client.models.action import (Action, RunnerType)


class ActionRunCommandTest(unittest2.TestCase):

    def test_get_params_types(self):
        runner = RunnerType()
        runner_params = {
            'foo': {'immutable': True},
            'bar': {'description': 'Some param.', 'type': 'string'}
        }
        runner.runner_parameters = runner_params

        action = Action()
        action.parameters = {
            'foo': {'immutable': False},  # Should not be allowed by API.
            'stuff': {'description': 'Some param.', 'type': 'string'}
        }

        # Simulating the worst case where required param is also immutable.
        runner.required_parameters = ['foo']
        action.required_parameters = ['stuff']

        params, rqd, opt, imm = ActionRunCommand._get_params_types(runner, action)
        self.assertEqual(len(params.keys()), 3)

        self.assertTrue('foo' in imm, '"foo" param should be in immutable set.')
        self.assertTrue('foo' not in rqd, '"foo" param should not be in required set.')
        self.assertTrue('foo' not in opt, '"foo" param should not be in optional set.')

        self.assertTrue('bar' in opt, '"bar" param should be in optional set.')
        self.assertTrue('bar' not in rqd, '"bar" param should not be in required set.')
        self.assertTrue('bar' not in imm, '"bar" param should not be in immutable set.')

        self.assertTrue('stuff' in rqd, '"stuff" param should be in required set.')
        self.assertTrue('stuff' not in opt, '"stuff" param should be in optional set.')
        self.assertTrue('stuff' not in imm, '"stuff" param should be in immutable set.')
