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

import bson
import copy

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.exceptions.trace import UniqueTraceNotFoundException
from st2common.models.api.trace import TraceContext
from st2common.persistence.trace import Trace
from st2common.services import trace as trace_service
from st2tests.fixturesloader import FixturesLoader
from st2tests import DbTestCase


FIXTURES_PACK = 'traces'

TEST_MODELS = {
    'executions': ['traceable_execution.yaml'],
    'liveactions': ['traceable_liveaction.yaml'],
    'traces': [
        'trace_empty.yaml',
        'trace_multiple_components.yaml',
        'trace_one_each.yaml',
        'trace_one_each_dup.yaml',
        'trace_execution.yaml'
    ]
}


class DummyComponent(object):
    def __init__(self, id_):
        self.id = id_


class TestTraceService(DbTestCase):

    models = None
    trace1 = None
    trace2 = None
    trace3 = None
    trace_empty = None
    trace_execution = None
    traceable_liveaction = None
    traceable_execution = None

    @classmethod
    def setUpClass(cls):
        super(TestTraceService, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.trace1 = cls.models['traces']['trace_multiple_components.yaml']
        cls.trace2 = cls.models['traces']['trace_one_each.yaml']
        cls.trace3 = cls.models['traces']['trace_one_each_dup.yaml']
        cls.trace_empty = cls.models['traces']['trace_empty.yaml']
        cls.trace_execution = cls.models['traces']['trace_execution.yaml']

        cls.traceable_liveaction = cls.models['liveactions']['traceable_liveaction.yaml']
        cls.traceable_execution = cls.models['executions']['traceable_execution.yaml']

    def test_get_trace_db_by_action_execution(self):
        action_execution = DummyComponent(id_=self.trace1.action_executions[0].object_id)
        trace_db = trace_service.get_trace_db_by_action_execution(action_execution=action_execution)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

    def test_get_trace_db_by_action_execution_fail(self):
        action_execution = DummyComponent(id_=self.trace2.action_executions[0].object_id)
        self.assertRaises(UniqueTraceNotFoundException,
                          trace_service.get_trace_db_by_action_execution,
                          **{'action_execution': action_execution})

    def test_get_trace_db_by_rule(self):
        rule = DummyComponent(id_=self.trace1.rules[0].object_id)
        trace_dbs = trace_service.get_trace_db_by_rule(rule=rule)
        self.assertEqual(len(trace_dbs), 1, 'Expected 1 trace_db.')
        self.assertEqual(trace_dbs[0].id, self.trace1.id, 'Incorrect trace_db returned.')

    def test_get_multiple_trace_db_by_rule(self):
        rule = DummyComponent(id_=self.trace2.rules[0].object_id)
        trace_dbs = trace_service.get_trace_db_by_rule(rule=rule)
        self.assertEqual(len(trace_dbs), 2, 'Expected 2 trace_db.')
        result = [trace_db.id for trace_db in trace_dbs]
        self.assertEqual(result, [self.trace2.id, self.trace3.id], 'Incorrect trace_dbs returned.')

    def test_get_trace_db_by_trigger_instance(self):
        trigger_instance = DummyComponent(id_=self.trace1.trigger_instances[0].object_id)
        trace_db = trace_service.get_trace_db_by_trigger_instance(trigger_instance=trigger_instance)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

    def test_get_trace_db_by_trigger_instance_fail(self):
        trigger_instance = DummyComponent(id_=self.trace2.trigger_instances[0].object_id)
        self.assertRaises(UniqueTraceNotFoundException,
                          trace_service.get_trace_db_by_trigger_instance,
                          **{'trigger_instance': trigger_instance})

    def test_get_trace_by_dict(self):
        trace_context = {'id_': str(self.trace1.id)}
        trace_db = trace_service.get_trace(trace_context)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

        trace_context = {'id_': str(bson.ObjectId())}
        self.assertRaises(StackStormDBObjectNotFoundError, trace_service.get_trace, trace_context)

        trace_context = {'trace_tag': self.trace1.trace_tag}
        trace_db = trace_service.get_trace(trace_context)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

    def test_get_trace_by_trace_context(self):
        trace_context = TraceContext(**{'id_': str(self.trace1.id)})
        trace_db = trace_service.get_trace(trace_context)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

        trace_context = TraceContext(**{'trace_tag': self.trace1.trace_tag})
        trace_db = trace_service.get_trace(trace_context)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

    def test_get_trace_ignore_trace_tag(self):
        trace_context = {'trace_tag': self.trace1.trace_tag}
        trace_db = trace_service.get_trace(trace_context)
        self.assertEqual(trace_db.id, self.trace1.id, 'Incorrect trace_db returned.')

        trace_context = {'trace_tag': self.trace1.trace_tag}
        trace_db = trace_service.get_trace(trace_context, ignore_trace_tag=True)
        self.assertEqual(trace_db, None, 'Should be None.')

    def test_get_trace_fail_empty_context(self):
        trace_context = {}
        self.assertRaises(ValueError, trace_service.get_trace, trace_context)

    def test_get_trace_fail_multi_match(self):
        trace_context = {'trace_tag': self.trace2.trace_tag}
        self.assertRaises(UniqueTraceNotFoundException, trace_service.get_trace, trace_context)

    def test_get_trace_db_by_live_action_valid_id_context(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        traceable_liveaction.context['trace_context'] = {'id_': str(self.trace_execution.id)}
        trace_db = trace_service.get_trace_db_by_live_action(traceable_liveaction)
        self.assertEqual(trace_db.id, self.trace_execution.id)

    def test_get_trace_db_by_live_action_trace_tag_context(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        traceable_liveaction.context['trace_context'] = {
            'trace_tag': str(self.trace_execution.trace_tag)
        }
        trace_db = trace_service.get_trace_db_by_live_action(traceable_liveaction)
        self.assertEqual(trace_db.id, None, 'Expected to be None')
        self.assertEqual(trace_db.trace_tag, str(self.trace_execution.trace_tag))

    def test_get_trace_db_by_live_action_parent(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        traceable_liveaction.context['parent'] = {
            'execution_id': str(self.trace1.action_executions[0].object_id)
        }
        trace_db = trace_service.get_trace_db_by_live_action(traceable_liveaction)
        self.assertEqual(trace_db.id, self.trace1.id)

    def test_get_trace_db_by_live_action_parent_fail(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        traceable_liveaction.context['parent'] = {
            'execution_id': str(bson.ObjectId())
        }
        self.assertRaises(StackStormDBObjectNotFoundError,
                          trace_service.get_trace_db_by_live_action,
                          traceable_liveaction)

    def test_get_trace_db_by_live_action_from_execution(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        # fixtures id value in liveaction is not persisted in DB.
        traceable_liveaction.id = bson.ObjectId(self.traceable_execution.liveaction['id'])
        trace_db = trace_service.get_trace_db_by_live_action(traceable_liveaction)
        self.assertEqual(trace_db.id, self.trace_execution.id)

    def test_get_trace_db_by_live_action_new_trace(self):
        traceable_liveaction = copy.copy(self.traceable_liveaction)
        # a liveaction without any associated ActionExecution
        traceable_liveaction.id = bson.ObjectId()
        trace_db = trace_service.get_trace_db_by_live_action(traceable_liveaction)
        self.assertEqual(trace_db.id, None, 'Should be None.')

    def test_add_or_update_given_trace_context(self):
        trace_context = {'id_': str(self.trace_empty.id)}
        action_execution_id = 'action_execution_1'
        rule_id = 'rule_1'
        trigger_instance_id = 'trigger_instance_1'
        trace_service.add_or_update_given_trace_context(
            trace_context,
            action_executions=[action_execution_id],
            rules=[rule_id],
            trigger_instances=[trigger_instance_id])

        retrieved_trace_db = Trace.get_by_id(self.trace_empty.id)
        self.assertEqual(len(retrieved_trace_db.action_executions), 1,
                         'Expected updated action_executions.')
        self.assertEqual(retrieved_trace_db.action_executions[0].object_id, action_execution_id,
                         'Expected updated action_executions.')

        self.assertEqual(len(retrieved_trace_db.rules), 1, 'Expected updated rules.')
        self.assertEqual(retrieved_trace_db.rules[0].object_id, rule_id, 'Expected updated rules.')

        self.assertEqual(len(retrieved_trace_db.trigger_instances), 1,
                         'Expected updated trigger_instances.')
        self.assertEqual(retrieved_trace_db.trigger_instances[0].object_id, trigger_instance_id,
                         'Expected updated trigger_instances.')

        Trace.delete(retrieved_trace_db)
        Trace.add_or_update(self.trace_empty)

    def test_add_or_update_given_trace_db(self):
        action_execution_id = 'action_execution_1'
        rule_id = 'rule_1'
        trigger_instance_id = 'trigger_instance_1'
        trace_service.add_or_update_given_trace_db(
            self.trace_empty,
            action_executions=[action_execution_id],
            rules=[rule_id],
            trigger_instances=[trigger_instance_id])

        retrieved_trace_db = Trace.get_by_id(self.trace_empty.id)
        self.assertEqual(len(retrieved_trace_db.action_executions), 1,
                         'Expected updated action_executions.')
        self.assertEqual(retrieved_trace_db.action_executions[0].object_id, action_execution_id,
                         'Expected updated action_executions.')

        self.assertEqual(len(retrieved_trace_db.rules), 1, 'Expected updated rules.')
        self.assertEqual(retrieved_trace_db.rules[0].object_id, rule_id, 'Expected updated rules.')

        self.assertEqual(len(retrieved_trace_db.trigger_instances), 1,
                         'Expected updated trigger_instances.')
        self.assertEqual(retrieved_trace_db.trigger_instances[0].object_id, trigger_instance_id,
                         'Expected updated trigger_instances.')

        Trace.delete(retrieved_trace_db)
        Trace.add_or_update(self.trace_empty)

    def test_add_or_update_given_trace_db_fail(self):
        self.assertRaises(ValueError, trace_service.add_or_update_given_trace_db, None)

    def test_add_or_update_given_trace_context_new(self):
        trace_context = {'trace_tag': 'awesome_test_trace'}
        action_execution_id = 'action_execution_1'
        rule_id = 'rule_1'
        trigger_instance_id = 'trigger_instance_1'

        pre_add_or_update_traces = len(Trace.get_all())
        trace_db = trace_service.add_or_update_given_trace_context(
            trace_context,
            action_executions=[action_execution_id],
            rules=[rule_id],
            trigger_instances=[trigger_instance_id])
        post_add_or_update_traces = len(Trace.get_all())

        self.assertTrue(post_add_or_update_traces > pre_add_or_update_traces,
                        'Expected new Trace to be created.')

        retrieved_trace_db = Trace.get_by_id(trace_db.id)
        self.assertEqual(len(retrieved_trace_db.action_executions), 1,
                         'Expected updated action_executions.')
        self.assertEqual(retrieved_trace_db.action_executions[0].object_id, action_execution_id,
                         'Expected updated action_executions.')

        self.assertEqual(len(retrieved_trace_db.rules), 1, 'Expected updated rules.')
        self.assertEqual(retrieved_trace_db.rules[0].object_id, rule_id, 'Expected updated rules.')

        self.assertEqual(len(retrieved_trace_db.trigger_instances), 1,
                         'Expected updated trigger_instances.')
        self.assertEqual(retrieved_trace_db.trigger_instances[0].object_id, trigger_instance_id,
                         'Expected updated trigger_instances.')

        Trace.delete(retrieved_trace_db)
