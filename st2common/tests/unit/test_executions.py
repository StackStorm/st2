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
import bson
import datetime

from st2tests.fixtures.packs import executions as fixture
from st2tests import DbTestCase
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.persistence.execution import ActionExecution
from st2common.models.api.execution import ActionExecutionAPI
from st2common.exceptions.db import StackStormDBObjectNotFoundError


class TestActionExecutionHistoryModel(DbTestCase):

    def setUp(self):
        super(TestActionExecutionHistoryModel, self).setUp()

        # Fake execution record for action liveactions triggered by workflow runner.
        self.fake_history_subtasks = [
            {
                'id': str(bson.ObjectId()),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'liveaction': copy.deepcopy(fixture.ARTIFACTS['liveactions']['task1']),
                'status': fixture.ARTIFACTS['liveactions']['task1']['status'],
                'start_timestamp': fixture.ARTIFACTS['liveactions']['task1']['start_timestamp'],
                'end_timestamp': fixture.ARTIFACTS['liveactions']['task1']['end_timestamp']
            },
            {
                'id': str(bson.ObjectId()),
                'action': copy.deepcopy(fixture.ARTIFACTS['actions']['local']),
                'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['run-local']),
                'liveaction': copy.deepcopy(fixture.ARTIFACTS['liveactions']['task2']),
                'status': fixture.ARTIFACTS['liveactions']['task2']['status'],
                'start_timestamp': fixture.ARTIFACTS['liveactions']['task2']['start_timestamp'],
                'end_timestamp': fixture.ARTIFACTS['liveactions']['task2']['end_timestamp']
            }
        ]

        # Fake execution record for a workflow action execution triggered by rule.
        self.fake_history_workflow = {
            'id': str(bson.ObjectId()),
            'trigger': copy.deepcopy(fixture.ARTIFACTS['trigger']),
            'trigger_type': copy.deepcopy(fixture.ARTIFACTS['trigger_type']),
            'trigger_instance': copy.deepcopy(fixture.ARTIFACTS['trigger_instance']),
            'rule': copy.deepcopy(fixture.ARTIFACTS['rule']),
            'action': copy.deepcopy(fixture.ARTIFACTS['actions']['chain']),
            'runner': copy.deepcopy(fixture.ARTIFACTS['runners']['action-chain']),
            'liveaction': copy.deepcopy(fixture.ARTIFACTS['liveactions']['workflow']),
            'children': [task['id'] for task in self.fake_history_subtasks],
            'status': fixture.ARTIFACTS['liveactions']['workflow']['status'],
            'start_timestamp': fixture.ARTIFACTS['liveactions']['workflow']['start_timestamp'],
            'end_timestamp': fixture.ARTIFACTS['liveactions']['workflow']['end_timestamp']
        }

        # Assign parent to the execution records for the subtasks.
        for task in self.fake_history_subtasks:
            task['parent'] = self.fake_history_workflow['id']

    def test_model_complete(self):

        # Create API object.
        obj = ActionExecutionAPI(**copy.deepcopy(self.fake_history_workflow))
        self.assertDictEqual(obj.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(obj.action, self.fake_history_workflow['action'])
        self.assertDictEqual(obj.runner, self.fake_history_workflow['runner'])
        self.assertEquals(obj.liveaction, self.fake_history_workflow['liveaction'])
        self.assertIsNone(getattr(obj, 'parent', None))
        self.assertListEqual(obj.children, self.fake_history_workflow['children'])

        # Convert API object to DB model.
        model = ActionExecutionAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(model.action, self.fake_history_workflow['action'])
        self.assertDictEqual(model.runner, self.fake_history_workflow['runner'])
        doc = copy.deepcopy(self.fake_history_workflow['liveaction'])
        doc['start_timestamp'] = doc['start_timestamp']
        doc['end_timestamp'] = doc['end_timestamp']
        self.assertDictEqual(model.liveaction, doc)
        self.assertIsNone(getattr(model, 'parent', None))
        self.assertListEqual(model.children, self.fake_history_workflow['children'])

        # Convert DB model to API object.
        obj = ActionExecutionAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(obj.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(obj.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(obj.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(obj.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(obj.action, self.fake_history_workflow['action'])
        self.assertDictEqual(obj.runner, self.fake_history_workflow['runner'])
        self.assertDictEqual(obj.liveaction, self.fake_history_workflow['liveaction'])
        self.assertIsNone(getattr(obj, 'parent', None))
        self.assertListEqual(obj.children, self.fake_history_workflow['children'])

    def test_crud_complete(self):
        # Create the DB record.
        obj = ActionExecutionAPI(**copy.deepcopy(self.fake_history_workflow))
        ActionExecution.add_or_update(ActionExecutionAPI.to_model(obj))
        model = ActionExecution.get_by_id(obj.id)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, self.fake_history_workflow['trigger'])
        self.assertDictEqual(model.trigger_type, self.fake_history_workflow['trigger_type'])
        self.assertDictEqual(model.trigger_instance, self.fake_history_workflow['trigger_instance'])
        self.assertDictEqual(model.rule, self.fake_history_workflow['rule'])
        self.assertDictEqual(model.action, self.fake_history_workflow['action'])
        self.assertDictEqual(model.runner, self.fake_history_workflow['runner'])
        doc = copy.deepcopy(self.fake_history_workflow['liveaction'])
        doc['start_timestamp'] = doc['start_timestamp']
        doc['end_timestamp'] = doc['end_timestamp']
        self.assertDictEqual(model.liveaction, doc)
        self.assertIsNone(getattr(model, 'parent', None))
        self.assertListEqual(model.children, self.fake_history_workflow['children'])

        # Update the DB record.
        children = [str(bson.ObjectId()), str(bson.ObjectId())]
        model.children = children
        ActionExecution.add_or_update(model)
        model = ActionExecution.get_by_id(obj.id)
        self.assertListEqual(model.children, children)

        # Delete the DB record.
        ActionExecution.delete(model)
        self.assertRaises(StackStormDBObjectNotFoundError, ActionExecution.get_by_id, obj.id)

    def test_model_partial(self):
        # Create API object.
        obj = ActionExecutionAPI(**copy.deepcopy(self.fake_history_subtasks[0]))
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(obj.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(obj.liveaction, self.fake_history_subtasks[0]['liveaction'])
        self.assertEqual(obj.parent, self.fake_history_subtasks[0]['parent'])
        self.assertIsNone(getattr(obj, 'children', None))

        # Convert API object to DB model.
        model = ActionExecutionAPI.to_model(obj)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(model.runner, self.fake_history_subtasks[0]['runner'])
        doc = copy.deepcopy(self.fake_history_subtasks[0]['liveaction'])
        doc['start_timestamp'] = doc['start_timestamp']
        doc['end_timestamp'] = doc['end_timestamp']

        self.assertDictEqual(model.liveaction, doc)
        self.assertEqual(model.parent, self.fake_history_subtasks[0]['parent'])
        self.assertListEqual(model.children, [])

        # Convert DB model to API object.
        obj = ActionExecutionAPI.from_model(model)
        self.assertEqual(str(model.id), obj.id)
        self.assertIsNone(getattr(obj, 'trigger', None))
        self.assertIsNone(getattr(obj, 'trigger_type', None))
        self.assertIsNone(getattr(obj, 'trigger_instance', None))
        self.assertIsNone(getattr(obj, 'rule', None))
        self.assertDictEqual(obj.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(obj.runner, self.fake_history_subtasks[0]['runner'])
        self.assertDictEqual(obj.liveaction, self.fake_history_subtasks[0]['liveaction'])
        self.assertEqual(obj.parent, self.fake_history_subtasks[0]['parent'])
        self.assertIsNone(getattr(obj, 'children', None))

    def test_crud_partial(self):
        # Create the DB record.
        obj = ActionExecutionAPI(**copy.deepcopy(self.fake_history_subtasks[0]))
        ActionExecution.add_or_update(ActionExecutionAPI.to_model(obj))
        model = ActionExecution.get_by_id(obj.id)
        self.assertEqual(str(model.id), obj.id)
        self.assertDictEqual(model.trigger, {})
        self.assertDictEqual(model.trigger_type, {})
        self.assertDictEqual(model.trigger_instance, {})
        self.assertDictEqual(model.rule, {})
        self.assertDictEqual(model.action, self.fake_history_subtasks[0]['action'])
        self.assertDictEqual(model.runner, self.fake_history_subtasks[0]['runner'])
        doc = copy.deepcopy(self.fake_history_subtasks[0]['liveaction'])
        doc['start_timestamp'] = doc['start_timestamp']
        doc['end_timestamp'] = doc['end_timestamp']
        self.assertDictEqual(model.liveaction, doc)
        self.assertEqual(model.parent, self.fake_history_subtasks[0]['parent'])
        self.assertListEqual(model.children, [])

        # Update the DB record.
        children = [str(bson.ObjectId()), str(bson.ObjectId())]
        model.children = children
        ActionExecution.add_or_update(model)
        model = ActionExecution.get_by_id(obj.id)
        self.assertListEqual(model.children, children)

        # Delete the DB record.
        ActionExecution.delete(model)
        self.assertRaises(StackStormDBObjectNotFoundError, ActionExecution.get_by_id, obj.id)

    def test_datetime_range(self):
        base = date_utils.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        for i in range(60):
            timestamp = base + datetime.timedelta(seconds=i)
            doc = copy.deepcopy(self.fake_history_subtasks[0])
            doc['id'] = str(bson.ObjectId())
            doc['start_timestamp'] = isotime.format(timestamp)
            obj = ActionExecutionAPI(**doc)
            ActionExecution.add_or_update(ActionExecutionAPI.to_model(obj))

        dt_range = '2014-12-25T00:00:10Z..2014-12-25T00:00:19Z'
        objs = ActionExecution.query(start_timestamp=dt_range)
        self.assertEqual(len(objs), 10)

        dt_range = '2014-12-25T00:00:19Z..2014-12-25T00:00:10Z'
        objs = ActionExecution.query(start_timestamp=dt_range)
        self.assertEqual(len(objs), 10)

    def test_sort_by_start_timestamp(self):
        base = date_utils.add_utc_tz(datetime.datetime(2014, 12, 25, 0, 0, 0))
        for i in range(60):
            timestamp = base + datetime.timedelta(seconds=i)
            doc = copy.deepcopy(self.fake_history_subtasks[0])
            doc['id'] = str(bson.ObjectId())
            doc['start_timestamp'] = isotime.format(timestamp)
            obj = ActionExecutionAPI(**doc)
            ActionExecution.add_or_update(ActionExecutionAPI.to_model(obj))

        dt_range = '2014-12-25T00:00:10Z..2014-12-25T00:00:19Z'
        objs = ActionExecution.query(start_timestamp=dt_range,
                                     order_by=['start_timestamp'])
        self.assertLess(objs[0]['start_timestamp'],
                        objs[9]['start_timestamp'])

        dt_range = '2014-12-25T00:00:19Z..2014-12-25T00:00:10Z'
        objs = ActionExecution.query(start_timestamp=dt_range,
                                     order_by=['-start_timestamp'])
        self.assertLess(objs[9]['start_timestamp'],
                        objs[0]['start_timestamp'])
