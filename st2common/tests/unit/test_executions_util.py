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

import six

from st2common.constants.action import LIVEACTION_STATUS_SCHEDULED
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.api.reactor import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.persistence.action import RunnerType, LiveAction
from st2common.persistence.execution import ActionExecution
import st2common.services.executions as executions_util
import st2common.util.action_db as action_utils

from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

import st2tests.config as tests_config
tests_config.parse_args()

FIXTURES_PACK = 'generic'

TEST_FIXTURES = {
    'liveactions': ['liveaction1.json', 'parentliveaction.json', 'childliveaction.json'],
    'actions': ['local.json'],
    'executions': ['execution1.json'],
    'runners': ['run-local.json'],
    'triggertypes': ['triggertype2.json'],
    'rules': ['rule3.json'],
    'triggers': ['trigger2.json'],
    'triggerinstances': ['trigger_instance_1.json']
}

DYNAMIC_FIXTURES = {
    'liveactions': ['liveaction3.json']
}


class ExecutionsUtilTestCase(CleanDbTestCase):
    def __init__(self, *args, **kwargs):
        super(ExecutionsUtilTestCase, self).__init__(*args, **kwargs)
        self.MODELS = None

    def setUp(self):
        super(ExecutionsUtilTestCase, self).setUp()
        self.MODELS = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                           fixtures_dict=TEST_FIXTURES)
        self.FIXTURES = FixturesLoader().load_fixtures(fixtures_pack=FIXTURES_PACK,
                                                       fixtures_dict=DYNAMIC_FIXTURES)

    def test_execution_creation_manual_action_run(self):
        liveaction = self.MODELS['liveactions']['liveaction1.json']
        executions_util.create_execution_object(liveaction)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertDictEqual(execution.trigger, {})
        self.assertDictEqual(execution.trigger_type, {})
        self.assertDictEqual(execution.trigger_instance, {})
        self.assertDictEqual(execution.rule, {})
        action = action_utils.get_action_by_ref('core.local')
        self.assertDictEqual(execution.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(execution.runner, vars(RunnerTypeAPI.from_model(runner)))
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEquals(execution.liveaction['id'], str(liveaction.id))

    def test_execution_creation_action_triggered_by_rule(self):
        # Wait for the action execution to complete and then confirm outcome.
        trigger_type = self.MODELS['triggertypes']['triggertype2.json']
        trigger = self.MODELS['triggers']['trigger2.json']
        trigger_instance = self.MODELS['triggerinstances']['trigger_instance_1.json']
        test_liveaction = self.FIXTURES['liveactions']['liveaction3.json']
        rule = self.MODELS['rules']['rule3.json']
        # Setup LiveAction to point to right rule and trigger_instance.
        # XXX: We need support for dynamic fixtures.
        test_liveaction['context']['rule']['id'] = str(rule.id)
        test_liveaction['context']['trigger_instance']['id'] = str(trigger_instance.id)
        test_liveaction_api = LiveActionAPI(**test_liveaction)
        test_liveaction = LiveAction.add_or_update(LiveActionAPI.to_model(test_liveaction_api))
        liveaction = LiveAction.get(context__trigger_instance__id=str(trigger_instance.id))
        self.assertIsNotNone(liveaction)
        self.assertEqual(liveaction.status, LIVEACTION_STATUS_SCHEDULED)
        executions_util.create_execution_object(liveaction)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertDictEqual(execution.trigger, vars(TriggerAPI.from_model(trigger)))
        self.assertDictEqual(execution.trigger_type, vars(TriggerTypeAPI.from_model(trigger_type)))
        self.assertDictEqual(execution.trigger_instance,
                             vars(TriggerInstanceAPI.from_model(trigger_instance)))
        self.assertDictEqual(execution.rule, vars(RuleAPI.from_model(rule)))
        action = action_utils.get_action_by_ref(liveaction.action)
        self.assertDictEqual(execution.action, vars(ActionAPI.from_model(action)))
        runner = RunnerType.get_by_name(action.runner_type['name'])
        self.assertDictEqual(execution.runner, vars(RunnerTypeAPI.from_model(runner)))
        liveaction = LiveAction.get_by_id(str(liveaction.id))
        self.assertEquals(execution.liveaction['id'], str(liveaction.id))

    def test_execution_creation_chains(self):
        """
        Test children and parent relationship is established.
        """
        childliveaction = self.MODELS['liveactions']['childliveaction.json']
        child_exec = executions_util.create_execution_object(childliveaction)
        parent_exection = self._get_action_execution(
            liveaction__id=childliveaction.context.get('parent', ''))
        child_execs = parent_exection.children
        self.assertTrue(str(child_exec.id) in child_execs)

    def _get_action_execution(self, **kwargs):
        return ActionExecution.get(**kwargs)


# descendants test section

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.json', 'child1_level1.json', 'child2_level1.json',
                   'child1_level2.json', 'child2_level2.json', 'child3_level2.json',
                   'child1_level3.json', 'child2_level3.json', 'child3_level3.json']
}


class ExecutionsUtilDescendantsTestCase(CleanDbTestCase):
    def __init__(self, *args, **kwargs):
        super(ExecutionsUtilDescendantsTestCase, self).__init__(*args, **kwargs)
        self.MODELS = None

    def setUp(self):
        super(ExecutionsUtilDescendantsTestCase, self).setUp()
        self.MODELS = FixturesLoader().save_fixtures_to_db(fixtures_pack=DESCENDANTS_PACK,
                                                           fixtures_dict=DESCENDANTS_FIXTURES)

    def test_get_all_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.json']
        all_descendants = executions_util.get_descendants(str(root_execution.id))

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_1_level_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.json']
        all_descendants = executions_util.get_descendants(str(root_execution.id),
                                                          descendant_depth=1)

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # All children of root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.parent == str(root_execution.id)]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)
