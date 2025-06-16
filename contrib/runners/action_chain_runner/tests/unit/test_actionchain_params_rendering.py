# -*- coding: utf-8 -*-
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
import unittest

import mock

from action_chain_runner import action_chain_runner as acr
from st2common.exceptions.action import ParameterRenderingFailedException
from st2common.models.system.actionchain import Node


class ActionChainRunnerResolveParamsTests(unittest.TestCase):
    def test_render_params_action_context(self):
        runner = acr.get_runner()
        chain_context = {
            "parent": {"execution_id": "some_awesome_exec_id", "user": "dad"},
            "user": "son",
            "k1": "v1",
        }
        task_params = {
            "exec_id": {"default": "{{action_context.parent.execution_id}}"},
            "k2": {},
            "foo": {"default": 1},
        }
        action_node = Node(
            name="test_action_context_params", ref="core.local", params=task_params
        )
        rendered_params = runner._resolve_params(action_node, {}, {}, {}, chain_context)
        self.assertEqual(rendered_params["exec_id"]["default"], "some_awesome_exec_id")

    def test_render_params_action_context_non_existent_member(self):
        runner = acr.get_runner()
        chain_context = {
            "parent": {"execution_id": "some_awesome_exec_id", "user": "dad"},
            "user": "son",
            "k1": "v1",
        }
        task_params = {
            "exec_id": {"default": "{{action_context.parent.yo_gimme_tha_key}}"},
            "k2": {},
            "foo": {"default": 1},
        }
        action_node = Node(
            name="test_action_context_params", ref="core.local", params=task_params
        )
        try:
            runner._resolve_params(action_node, {}, {}, {}, chain_context)
            self.fail(
                "Should have thrown an instance of %s"
                % ParameterRenderingFailedException
            )
        except ParameterRenderingFailedException:
            pass

    def test_render_params_with_config(self):
        with mock.patch(
            "st2common.util.config_loader.ContentPackConfigLoader"
        ) as config_loader:
            config_loader().get_config.return_value = {
                "amazing_config_value_fo_lyfe": "no"
            }

            runner = acr.get_runner()
            chain_context = {
                "parent": {
                    "execution_id": "some_awesome_exec_id",
                    "user": "dad",
                    "pack": "mom",
                },
                "user": "son",
            }
            task_params = {
                "config_val": "{{config_context.amazing_config_value_fo_lyfe}}"
            }
            action_node = Node(
                name="test_action_context_params", ref="core.local", params=task_params
            )
            rendered_params = runner._resolve_params(
                action_node, {}, {}, {}, chain_context
            )
            self.assertEqual(rendered_params["config_val"], "no")

    def test_init_params_vars_with_unicode_value(self):
        chain_spec = {
            "vars": {
                "unicode_var": "٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ ćšž",
                "unicode_var_param": "{{ param }}",
            },
            "chain": [
                {
                    "name": "c1",
                    "ref": "core.local",
                    "parameters": {"cmd": "echo {{ unicode_var }}"},
                }
            ],
        }

        chain_holder = acr.ChainHolder(chainspec=chain_spec, chainname="foo")
        chain_holder.init_vars(action_parameters={"param": "٩(̾●̮̮̃̾•̃̾)۶"})

        expected = {
            "unicode_var": "٩(̾●̮̮̃̾•̃̾)۶ ٩(̾●̮̮̃̾•̃̾)۶ ćšž",
            "unicode_var_param": "٩(̾●̮̮̃̾•̃̾)۶",
        }
        self.assertEqual(chain_holder.vars, expected)
