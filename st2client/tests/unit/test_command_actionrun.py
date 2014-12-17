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
