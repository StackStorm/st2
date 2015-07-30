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

import unittest2

from st2actions.runners import actionchainrunner as acr
from st2common.exceptions.action import ParameterRenderingFailedException
from st2common.models.system.actionchain import Node


class ActionChainRunnerResolveParamsTests(unittest2.TestCase):

    def test_render_params_action_context(self):
        runner = acr.get_runner()
        chain_context = {
            'parent': {
                'execution_id': 'some_awesome_exec_id',
                'user': 'dad'
            },
            'user': 'son',
            'k1': 'v1'
        }
        task_params = {
            'exec_id': {'default': '{{action_context.parent.execution_id}}'},
            'k2': {},
            'foo': {'default': 1}
        }
        action_node = Node(name='test_action_context_params', ref='core.local', params=task_params)
        rendered_params = runner._resolve_params(action_node, {}, {}, {}, chain_context)
        self.assertEqual(rendered_params['exec_id']['default'], 'some_awesome_exec_id')

    def test_render_params_action_context_non_existent_member(self):
        runner = acr.get_runner()
        chain_context = {
            'parent': {
                'execution_id': 'some_awesome_exec_id',
                'user': 'dad'
            },
            'user': 'son',
            'k1': 'v1'
        }
        task_params = {
            'exec_id': {'default': '{{action_context.parent.yo_gimme_tha_key}}'},
            'k2': {},
            'foo': {'default': 1}
        }
        action_node = Node(name='test_action_context_params', ref='core.local', params=task_params)
        try:
            runner._resolve_params(action_node, {}, {}, {}, chain_context)
            self.fail('Should have thrown an instance of %s' % ParameterRenderingFailedException)
        except ParameterRenderingFailedException:
            pass
