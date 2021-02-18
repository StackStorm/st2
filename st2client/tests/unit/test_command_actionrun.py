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
import copy

import unittest2
import six
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
        self.assertEqual(len(list(params.keys())), 3)

        self.assertIn('foo', imm, '"foo" param should be in immutable set.')
        self.assertNotIn('foo', rqd, '"foo" param should not be in required set.')
        self.assertNotIn('foo', opt, '"foo" param should not be in optional set.')

        self.assertIn('bar', opt, '"bar" param should be in optional set.')
        self.assertNotIn('bar', rqd, '"bar" param should not be in required set.')
        self.assertNotIn('bar', imm, '"bar" param should not be in immutable set.')

        self.assertIn('stuff', rqd, '"stuff" param should be in required set.')
        self.assertNotIn('stuff', opt, '"stuff" param should not be in optional set.')
        self.assertNotIn('stuff', imm, '"stuff" param should not be in immutable set.')
        self.assertEqual(runner.runner_parameters, orig_runner_params, 'Runner params modified.')
        self.assertEqual(action.parameters, orig_action_params, 'Action params modified.')

    def test_opt_in_dict_auto_convert(self):
        """Test ability for user to opt-in to dict convert functionality
        """

        runner = RunnerType()
        runner.runner_parameters = {}

        action = Action()
        action.ref = 'test.action'
        action.parameters = {
            'param_array': {'type': 'array'},
        }

        subparser = mock.Mock()
        command = ActionRunCommand(action, self, subparser, name='test')

        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.parameters = [
            'param_array=foo:bar,foo2:bar2',
        ]

        mockarg.auto_dict = False
        param = command._get_action_parameters_from_args(action=action, runner=runner, args=mockarg)
        self.assertEqual(param['param_array'], ['foo:bar', 'foo2:bar2'])

        mockarg.auto_dict = True
        param = command._get_action_parameters_from_args(action=action, runner=runner, args=mockarg)
        self.assertEqual(param['param_array'], [{'foo': 'bar', 'foo2': 'bar2'}])

        # set auto_dict back to default
        mockarg.auto_dict = False

    def test_get_params_from_args(self):
        """test_get_params_from_args

        This tests the details of the auto-dict conversion, assuming it's enabled. Please
        see test_opt_in_dict_auto_convert for a test of detecting whether or not this
        functionality is enabled.
        """

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
            'param_array_of_dicts': {'type': 'array', 'properties': {
                'foo': {'type': 'string'},
                'bar': {'type': 'integer'},
                'baz': {'type': 'number'},
                'qux': {'type': 'object'},
                'quux': {'type': 'boolean'}}
            },
        }

        subparser = mock.Mock()
        command = ActionRunCommand(action, self, subparser, name='test')

        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.auto_dict = True
        mockarg.parameters = [
            'param_string=hoge',
            'param_integer=123',
            'param_number=1.23',
            'param_object=hoge=1,fuga=2',
            'param_boolean=False',
            'param_array=foo,bar,baz',
            'param_array_of_dicts=foo:HOGE,bar:1,baz:1.23,qux:foo=bar,quux:True',
            'param_array_of_dicts=foo:FUGA,bar:2,baz:2.34,qux:bar=baz,quux:False'
        ]

        param = command._get_action_parameters_from_args(action=action, runner=runner, args=mockarg)

        self.assertIsInstance(param, dict)
        self.assertEqual(param['param_string'], 'hoge')
        self.assertEqual(param['param_integer'], 123)
        self.assertEqual(param['param_number'], 1.23)
        self.assertEqual(param['param_object'], {'hoge': '1', 'fuga': '2'})
        self.assertFalse(param['param_boolean'])
        self.assertEqual(param['param_array'], ['foo', 'bar', 'baz'])

        # checking the result of parsing for array of objects
        self.assertIsInstance(param['param_array_of_dicts'], list)
        self.assertEqual(len(param['param_array_of_dicts']), 2)
        for param in param['param_array_of_dicts']:
            self.assertIsInstance(param, dict)
            self.assertIsInstance(param['foo'], str)
            self.assertIsInstance(param['bar'], int)
            self.assertIsInstance(param['baz'], float)
            self.assertIsInstance(param['qux'], dict)
            self.assertIsInstance(param['quux'], bool)

        # set auto_dict back to default
        mockarg.auto_dict = False

    def test_get_params_from_args_read_content_from_file(self):
        runner = RunnerType()
        runner.runner_parameters = {}

        action = Action()
        action.ref = 'test.action'
        action.parameters = {
            'param_object': {'type': 'object'},
        }

        subparser = mock.Mock()
        command = ActionRunCommand(action, self, subparser, name='test')

        # 1. File doesn't exist
        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.auto_dict = True
        mockarg.parameters = [
            '@param_object=doesnt-exist.json'
        ]

        self.assertRaisesRegex(ValueError, "doesn't exist",
                               command._get_action_parameters_from_args, action=action,
                               runner=runner, args=mockarg)

        # 2. Valid file path (we simply read this file)
        mockarg = mock.Mock()
        mockarg.inherit_env = False
        mockarg.auto_dict = True
        mockarg.parameters = [
            '@param_string=%s' % (__file__)
        ]

        params = command._get_action_parameters_from_args(action=action,
                                 runner=runner, args=mockarg)
        self.assertTrue(isinstance(params["param_string"], six.text_type))
        self.assertTrue(params["param_string"].startswith("# Copyright"))

    def test_get_params_from_args_with_multiple_declarations(self):
        """test_get_params_from_args_with_multiple_declarations

        This tests the details of the auto-dict conversion, assuming it's enabled. Please
        see test_opt_in_dict_auto_convert for a test of detecting whether or not this
        functionality is enabled.
        """

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
        mockarg.auto_dict = True
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

        # set auto_dict back to default
        mockarg.auto_dict = False
