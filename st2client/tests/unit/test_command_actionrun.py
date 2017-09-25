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

import copy

import unittest2
import mock

from st2client.commands.action import ActionRunCommand
from st2client.models.action import (Action, RunnerType)


class ActionRunCommandTest(unittest2.TestCase):

    def test_get_params_types(self):
        runner = RunnerType()
        runner_params = {
            'foo': {'immutable': True, 'required': True},
            'bar': {'description': 'Some param.', 'type': 'string'}
        }
        runner.runner_parameters = runner_params
        orig_runner_params = copy.deepcopy(runner.runner_parameters)

        action = Action()
        action.parameters = {
            'foo': {'immutable': False},  # Should not be allowed by API.
            'stuff': {'description': 'Some param.', 'type': 'string', 'required': True}
        }
        orig_action_params = copy.deepcopy(action.parameters)

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
        self.assertEqual(runner.runner_parameters, orig_runner_params, 'Runner params modified.')
        self.assertEqual(action.parameters, orig_action_params, 'Action params modified.')

    def test_get_params_from_args(self):
        runner = RunnerType()
        runner.runner_parameters = {}

        action = Action()
        action.ref = 'test.action'
        action.parameters = {
            'param_string': {'type': 'string'},
            'param_integer': {'type': 'integer'},
            'param_number': {'type': 'number'},
            'param_object': {'type': 'object'},
            'param_boolean': {'type': 'boolean'},
            'param_array': {'type': 'array'},
            'param_array_of_dicts': {'type': 'array'},
        }

        subparser = mock.Mock()
        command = ActionRunCommand(action, self, subparser, name='test')

        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.parameters = [
            'param_string=hoge',
            'param_integer=123',
            'param_number=1.23',
            'param_object=hoge=1,fuga=2',
            'param_boolean=False',
            'param_array=foo,bar,baz',
            'param_array_of_dicts=foo:1,bar:2'
        ]

        param = command._get_action_parameters_from_args(action=action, runner=runner, args=mockarg)

        self.assertTrue(isinstance(param, dict))
        self.assertEqual(param['param_string'], 'hoge')
        self.assertEqual(param['param_integer'], 123)
        self.assertEqual(param['param_number'], 1.23)
        self.assertEqual(param['param_object'], {'hoge': '1', 'fuga': '2'})
        self.assertFalse(param['param_boolean'])
        self.assertEqual(param['param_array'], ['foo', 'bar', 'baz'])
        self.assertEqual(param['param_array_of_dicts'], [{'foo': '1', 'bar': '2'}])

    def test_get_params_from_args_with_multiple_declarations(self):
        runner = RunnerType()
        runner.runner_parameters = {}

        action = Action()
        action.ref = 'test.action'
        action.parameters = {
            'param_string': {'type': 'string'},
            'param_array': {'type': 'array'},
            'param_array_of_dicts': {'type': 'array'},
        }

        subparser = mock.Mock()
        command = ActionRunCommand(action, self, subparser, name='test')

        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.parameters = [
            'param_string=hoge',  # This value will be overwritten with the next declaration.
            'param_string=fuga',
            'param_array=foo',
            'param_array=bar',
            'param_array_of_dicts=foo:1,bar:2',
            'param_array_of_dicts=hoge:A,fuga:B'
        ]

        param = command._get_action_parameters_from_args(action=action, runner=runner, args=mockarg)

        # checks to accept multiple declaration only if the array type
        self.assertEqual(param['param_string'], 'fuga')
        self.assertEqual(param['param_array'], ['foo', 'bar'])
        self.assertEqual(param['param_array_of_dicts'], [
            {'foo': '1', 'bar': '2'},
            {'hoge': 'A', 'fuga': 'B'}
        ])
