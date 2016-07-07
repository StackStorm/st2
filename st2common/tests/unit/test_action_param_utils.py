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
import six

from st2common.models.utils import action_param_utils
from st2common.models.api.action import RunnerTypeAPI, ActionAPI
from st2common.persistence.action import Action
from st2common.persistence.runner import RunnerType
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader


TEST_FIXTURES = {
    'actions': [
        'action1.yaml',
        'action3.yaml'
    ],
    'runners': [
        'testrunner1.yaml',
        'testrunner3.yaml'
    ]
}

PACK = 'generic'
LOADER = FixturesLoader()
FIXTURES = LOADER.load_fixtures(fixtures_pack=PACK, fixtures_dict=TEST_FIXTURES)


class ActionParamsUtilsTest(DbTestCase):

    @classmethod
    def setUpClass(cls):
        super(ActionParamsUtilsTest, cls).setUpClass()

        cls.runnertype_dbs = {}
        cls.action_dbs = {}

        for _, fixture in six.iteritems(FIXTURES['runners']):
            instance = RunnerTypeAPI(**fixture)
            runnertype_db = RunnerType.add_or_update(RunnerTypeAPI.to_model(instance))
            cls.runnertype_dbs[runnertype_db.name] = runnertype_db

        for _, fixture in six.iteritems(FIXTURES['actions']):
            instance = ActionAPI(**fixture)
            action_db = Action.add_or_update(ActionAPI.to_model(instance))
            cls.action_dbs[action_db.name] = action_db

    def test_merge_action_runner_params_meta(self):
        required, optional, immutable = action_param_utils.get_params_view(
            action_db=self.action_dbs['action-1'],
            runner_db=self.runnertype_dbs['test-runner-1'])
        merged = {}
        merged.update(required)
        merged.update(optional)
        merged.update(immutable)

        consolidated = action_param_utils.get_params_view(
            action_db=self.action_dbs['action-1'],
            runner_db=self.runnertype_dbs['test-runner-1'],
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
            self.runnertype_dbs['test-runner-1'].runner_parameters['runnerdummy'])
        action_meta = copy.deepcopy(self.action_dbs['action-1'].parameters['runnerdummy'])
        merged_meta = action_param_utils._merge_param_meta_values(action_meta=action_meta,
                                                                  runner_meta=runner_meta)

        # Description is in runner meta but not in action meta.
        self.assertEqual(merged_meta['description'], runner_meta['description'])
        # Default value is overridden in action.
        self.assertEqual(merged_meta['default'], action_meta['default'])
        # Immutability is set in action.
        self.assertEqual(merged_meta['immutable'], action_meta['immutable'])

    def test_merge_param_meta_require_override(self):
        action_meta = {
            'required': False
        }
        runner_meta = {
            'required': True
        }
        merged_meta = action_param_utils._merge_param_meta_values(action_meta=action_meta,
                                                                  runner_meta=runner_meta)

        self.assertEqual(merged_meta['required'], action_meta['required'])

    def test_validate_action_inputs(self):
        requires, unexpected = action_param_utils.validate_action_parameters(
            self.action_dbs['action-1'].ref, {'foo': 'bar'})

        self.assertListEqual(requires, ['actionstr'])
        self.assertListEqual(unexpected, ['foo'])

    def test_validate_overridden_action_inputs(self):
        requires, unexpected = action_param_utils.validate_action_parameters(
            self.action_dbs['action-3'].ref, {'k1': 'foo'})

        self.assertListEqual(requires, [])
        self.assertListEqual(unexpected, [])
