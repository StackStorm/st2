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

import mock
import six

from st2common.constants import action as action_constants
from st2common.models.api.action import RunnerTypeAPI, ActionAPI, LiveActionAPI
from st2common.models.api.trigger import TriggerTypeAPI, TriggerAPI, TriggerInstanceAPI
from st2common.models.api.rule import RuleAPI
from st2common.persistence.liveaction import LiveAction
from st2common.persistence.runner import RunnerType
from st2common.persistence.execution import ActionExecution
from st2common.transport.publishers import PoolPublisher
import st2common.services.executions as executions_util
import st2common.util.action_db as action_utils
import st2common.util.date as date_utils

from st2tests.base import CleanDbTestCase
from st2tests.fixturesloader import FixturesLoader

import st2tests.config as tests_config
tests_config.parse_args()

FIXTURES_PACK = 'generic'

TEST_FIXTURES = {
    'liveactions': ['liveaction1.yaml', 'parentliveaction.yaml', 'childliveaction.yaml',
                    'successful_liveaction.yaml'],
    'actions': ['local.yaml'],
    'executions': ['execution1.yaml'],
    'runners': ['run-local.yaml'],
    'triggertypes': ['triggertype2.yaml'],
    'rules': ['rule3.yaml'],
    'triggers': ['trigger2.yaml'],
    'triggerinstances': ['trigger_instance_1.yaml']
}

DYNAMIC_FIXTURES = {
    'liveactions': ['liveaction3.yaml']
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
        liveaction = self.MODELS['liveactions']['liveaction1.yaml']
        pre_creation_timestamp = date_utils.get_datetime_utc_now()
        executions_util.create_execution_object(liveaction)
        post_creation_timestamp = date_utils.get_datetime_utc_now()
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
        self.assertEquals(len(execution.log), 1)
        self.assertEquals(execution.log[0]['status'], liveaction.status)
        self.assertGreater(execution.log[0]['timestamp'], pre_creation_timestamp)
        self.assertLess(execution.log[0]['timestamp'], post_creation_timestamp)

    def test_execution_creation_action_triggered_by_rule(self):
        # Wait for the action execution to complete and then confirm outcome.
        trigger_type = self.MODELS['triggertypes']['triggertype2.yaml']
        trigger = self.MODELS['triggers']['trigger2.yaml']
        trigger_instance = self.MODELS['triggerinstances']['trigger_instance_1.yaml']
        test_liveaction = self.FIXTURES['liveactions']['liveaction3.yaml']
        rule = self.MODELS['rules']['rule3.yaml']
        # Setup LiveAction to point to right rule and trigger_instance.
        # XXX: We need support for dynamic fixtures.
        test_liveaction['context']['rule']['id'] = str(rule.id)
        test_liveaction['context']['trigger_instance']['id'] = str(trigger_instance.id)
        test_liveaction_api = LiveActionAPI(**test_liveaction)
        test_liveaction = LiveAction.add_or_update(LiveActionAPI.to_model(test_liveaction_api))
        liveaction = LiveAction.get(context__trigger_instance__id=str(trigger_instance.id))
        self.assertIsNotNone(liveaction)
        self.assertEqual(liveaction.status, action_constants.LIVEACTION_STATUS_REQUESTED)
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

    def test_execution_creation_with_web_url(self):
        liveaction = self.MODELS['liveactions']['liveaction1.yaml']
        executions_util.create_execution_object(liveaction)
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertTrue(execution.web_url is not None)
        execution_id = str(execution.id)
        self.assertTrue(('history/%s/general' % execution_id) in execution.web_url)

    def test_execution_creation_chains(self):
        childliveaction = self.MODELS['liveactions']['childliveaction.yaml']
        child_exec = executions_util.create_execution_object(childliveaction)
        parent_execution_id = childliveaction.context['parent']['execution_id']
        parent_execution = ActionExecution.get_by_id(parent_execution_id)
        child_execs = parent_execution.children
        self.assertTrue(str(child_exec.id) in child_execs)

    def test_execution_update(self):
        liveaction = self.MODELS['liveactions']['liveaction1.yaml']
        executions_util.create_execution_object(liveaction)
        liveaction.status = 'running'
        pre_update_timestamp = date_utils.get_datetime_utc_now()
        executions_util.update_execution(liveaction)
        post_update_timestamp = date_utils.get_datetime_utc_now()
        execution = self._get_action_execution(liveaction__id=str(liveaction.id),
                                               raise_exception=True)
        self.assertEquals(len(execution.log), 2)
        self.assertEquals(execution.log[1]['status'], liveaction.status)
        self.assertGreater(execution.log[1]['timestamp'], pre_update_timestamp)
        self.assertLess(execution.log[1]['timestamp'], post_update_timestamp)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def test_abandon_executions(self):
        liveaction_db = self.MODELS['liveactions']['liveaction1.yaml']
        executions_util.create_execution_object(liveaction_db)
        execution_db = executions_util.abandon_execution_if_incomplete(
            liveaction_id=str(liveaction_db.id))
        self.assertEquals(execution_db.status, 'abandoned')

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def test_abandon_executions_on_complete(self):
        liveaction_db = self.MODELS['liveactions']['successful_liveaction.yaml']
        executions_util.create_execution_object(liveaction_db)
        expected_msg = 'LiveAction %s already in a completed state %s\.' % \
                       (str(liveaction_db.id), liveaction_db.status)
        self.assertRaisesRegexp(ValueError, expected_msg,
                                executions_util.abandon_execution_if_incomplete,
                                liveaction_id=str(liveaction_db.id))

    def _get_action_execution(self, **kwargs):
        return ActionExecution.get(**kwargs)


# descendants test section

DESCENDANTS_PACK = 'descendants'

DESCENDANTS_FIXTURES = {
    'executions': ['root_execution.yaml', 'child1_level1.yaml', 'child2_level1.yaml',
                   'child1_level2.yaml', 'child2_level2.yaml', 'child3_level2.yaml',
                   'child1_level3.yaml', 'child2_level3.yaml', 'child3_level3.yaml']
}


class ExecutionsUtilDescendantsTestCase(CleanDbTestCase):
    def __init__(self, *args, **kwargs):
        super(ExecutionsUtilDescendantsTestCase, self).__init__(*args, **kwargs)
        self.MODELS = None

    def setUp(self):
        super(ExecutionsUtilDescendantsTestCase, self).setUp()
        self.MODELS = FixturesLoader().save_fixtures_to_db(fixtures_pack=DESCENDANTS_PACK,
                                                           fixtures_dict=DESCENDANTS_FIXTURES)

    def test_get_all_descendants_sorted(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        all_descendants = executions_util.get_descendants(str(root_execution.id),
                                                          result_fmt='sorted')

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

        # verify sort order
        for idx in range(len(all_descendants) - 1):
            self.assertLess(all_descendants[idx].start_timestamp,
                            all_descendants[idx + 1].start_timestamp)

    def test_get_all_descendants(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        all_descendants = executions_util.get_descendants(str(root_execution.id))

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.id != root_execution.id]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_1_level_descendants_sorted(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        all_descendants = executions_util.get_descendants(str(root_execution.id),
                                                          descendant_depth=1,
                                                          result_fmt='sorted')

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # All children of root_execution
        expected_ids = [str(v.id) for _, v in six.iteritems(self.MODELS['executions'])
                        if v.parent == str(root_execution.id)]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

        # verify sort order
        for idx in range(len(all_descendants) - 1):
            self.assertLess(all_descendants[idx].start_timestamp,
                            all_descendants[idx + 1].start_timestamp)

    def test_get_2_level_descendants_sorted(self):
        root_execution = self.MODELS['executions']['root_execution.yaml']
        all_descendants = executions_util.get_descendants(str(root_execution.id),
                                                          descendant_depth=2,
                                                          result_fmt='sorted')

        all_descendants_ids = [str(descendant.id) for descendant in all_descendants]
        all_descendants_ids.sort()

        # All children of root_execution
        root_execution = self.MODELS['executions']['root_execution.yaml']
        expected_ids = []
        traverse = [(child_id, 1) for child_id in root_execution.children]
        while traverse:
            node_id, level = traverse.pop(0)
            expected_ids.append(node_id)
            children = self._get_action_execution(node_id).children
            if children and level < 2:
                traverse.extend([(child_id, level + 1) for child_id in children])
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def _get_action_execution(self, ae_id):
        for _, execution in six.iteritems(self.MODELS['executions']):
            if str(execution.id) == ae_id:
                return execution
        return None
