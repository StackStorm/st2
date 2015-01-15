# -*- coding: utf-8 -*-
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

from unittest2 import TestCase
from st2common.models.api.action import RunnerTypeAPI
from st2common.models.db.action import ActionDB
from st2common.models.utils import action_param_utils


class ActionParamsUtilsTest(TestCase):
    action_db = None
    runnertype_db = None

    @classmethod
    def setUpClass(cls):
        super(ActionParamsUtilsTest, cls).setUpClass()
        # TODO(manas): Use fixtures
        ActionParamsUtilsTest._setup_test_models()

    def test_merge_action_runner_params_meta(self):
        required, optional, immutable = action_param_utils.get_params_view(
            action_db=ActionParamsUtilsTest.action_db,
            runner_db=ActionParamsUtilsTest.runnertype_db)
        merged = {}
        merged.update(required)
        merged.update(optional)
        merged.update(immutable)

        consolidated = action_param_utils.get_params_view(
            action_db=ActionParamsUtilsTest.action_db,
            runner_db=ActionParamsUtilsTest.runnertype_db,
            merged_only=True)

        # Validate that merged_only view works.
        self.assertEqual(merged, consolidated)

        # Validate required params.
        self.assertEqual(len(required), 1, 'Required should contain only one param.')
        self.assertTrue('actionstr' in required, 'actionstr param is a required param.')
        self.assertTrue('actionstr' not in optional and 'actionstr' not in immutable and
                        'actionstr' in merged)

        # Validate immutable params.
        self.assertTrue('runnerimmutable' in immutable, 'runnerimmutable should be in immutable.')
        self.assertTrue('actionimmutable' in immutable, 'actionimmutable should be in immutable.')

        # Validate optional params.
        for opt in optional:
            self.assertTrue(opt not in required and opt not in immutable and opt in merged,
                            'Optional parameter %s failed validation.' % opt)

    def test_merge_param_meta_values(self):
        runner_meta = copy.deepcopy(
            ActionParamsUtilsTest.runnertype_db.runner_parameters['runnerdummy'])
        action_meta = copy.deepcopy(ActionParamsUtilsTest.action_db.parameters['runnerdummy'])
        merged_meta = action_param_utils._merge_param_meta_values(action_meta=action_meta,
                                                                  runner_meta=runner_meta)

        # Description is in runner meta but not in action meta.
        self.assertEqual(merged_meta['description'], runner_meta['description'])
        # Default value is overridden in action.
        self.assertEqual(merged_meta['default'], action_meta['default'])
        # Immutability is set in action.
        self.assertEqual(merged_meta['immutable'], action_meta['immutable'])

    @classmethod
    def _setup_test_models(cls):
        ActionParamsUtilsTest._setup_runner_models()
        ActionParamsUtilsTest._setup_action_models()

    @classmethod
    def _setup_runner_models(cls):
        test_runner = {
            'name': 'test-runner',
            'description': 'A test runner.',
            'enabled': True,
            'runner_parameters': {
                'runnerstr': {
                    'description': 'Foo str param.',
                    'type': 'string',
                    'default': 'defaultfoo'
                },
                'runnerint': {
                    'description': 'Foo int param.',
                    'type': 'number'
                },
                'runnerfoo': {
                    'description': 'Some foo param.',
                    'default': 'FOO'
                },
                'runnerdummy': {
                    'description': 'Dummy param.',
                    'type': 'string',
                    'default': 'runnerdummy'
                },
                'runnerimmutable': {
                    'description': 'Immutable param.',
                    'type': 'string',
                    'default': 'runnerimmutable',
                    'immutable': True
                }
            },
            'runner_module': 'tests.test_runner'
        }
        runnertype_api = RunnerTypeAPI(**test_runner)
        ActionParamsUtilsTest.runnertype_db = RunnerTypeAPI.to_model(runnertype_api)

    @classmethod
    def _setup_action_models(cls):
        action_db = ActionDB()
        action_db.name = 'action-1'
        action_db.description = 'awesomeness'
        action_db.enabled = True
        action_db.pack = 'wolfpack'
        action_db.entry_point = ''
        action_db.runner_type = {'name': 'test-runner'}
        action_db.parameters = {
            'actionstr': {'type': 'string', 'required': True},
            'actionint': {'type': 'number', 'default': 10},
            'runnerdummy': {'type': 'string', 'default': 'actiondummy', 'immutable': True},
            'runnerfoo': {'type': 'string', 'immutable': True},
            'runnerimmutable': {'type': 'string', 'default': 'failed_override'},
            'actionimmutable': {'type': 'string', 'default': 'actionimmutable', 'immutable': True}
        }
        ActionParamsUtilsTest.action_db = action_db
