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

from st2common.models.db.trace import TraceDB, TraceComponentDB
from st2common.persistence.trace import Trace

from st2tests.base import CleanDbTestCase


class TraceDBTest(CleanDbTestCase):

    def test_get(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag='test_trace',
            action_executions=[str(bson.ObjectId()) for _ in range(4)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(5)])
        retrieved = Trace.get(id=saved.id)
        self.assertEquals(retrieved.id, saved.id, 'Incorrect trace retrieved.')

    def test_query(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag='test_trace',
            action_executions=[str(bson.ObjectId()) for _ in range(4)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(5)])
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEquals(len(retrieved), 1, 'Should have 1 trace.')
        self.assertEquals(retrieved[0].id, saved.id, 'Incorrect trace retrieved.')

        # Add another trace with same trace_tag and confirm that we support.
        # This is most likley an anti-pattern for the trace_tag but it is an unknown.
        saved = TraceDBTest._create_save_trace(
            trace_tag='test_trace',
            action_executions=[str(bson.ObjectId()) for _ in range(2)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(3)])
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEquals(len(retrieved), 2, 'Should have 2 traces.')

    def test_update(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag='test_trace',
            action_executions=[],
            rules=[],
            trigger_instances=[])
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEquals(len(retrieved), 1, 'Should have 1 trace.')
        self.assertEquals(retrieved[0].id, saved.id, 'Incorrect trace retrieved.')

        no_action_executions = 4
        no_rules = 4
        no_trigger_instances = 5
        saved = TraceDBTest._create_save_trace(
            trace_tag='test_trace',
            id_=retrieved[0].id,
            action_executions=[str(bson.ObjectId()) for _ in range(no_action_executions)],
            rules=[str(bson.ObjectId()) for _ in range(no_rules)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(no_trigger_instances)])
        retrieved = Trace.query(trace_tag=saved.trace_tag)

        self.assertEquals(len(retrieved), 1, 'Should have 1 trace.')
        self.assertEquals(retrieved[0].id, saved.id, 'Incorrect trace retrieved.')
        # validate update
        self.assertEquals(len(retrieved[0].action_executions), no_action_executions,
                          'Failed to update action_executions.')
        self.assertEquals(len(retrieved[0].rules), no_rules, 'Failed to update rules.')
        self.assertEquals(len(retrieved[0].trigger_instances), no_trigger_instances,
                          'Failed to update trigger_instances.')

    @staticmethod
    def _create_save_trace(trace_tag, id_=None, action_executions=None, rules=None,
                           trigger_instances=None):

        if action_executions is None:
            action_executions = []
        action_executions = [TraceComponentDB(object_id=action_execution)
                             for action_execution in action_executions]

        if rules is None:
            rules = []
        rules = [TraceComponentDB(object_id=rule) for rule in rules]

        if trigger_instances is None:
            trigger_instances = []
        trigger_instances = [TraceComponentDB(object_id=trigger_instance)
                             for trigger_instance in trigger_instances]

        created = TraceDB(id=id_,
                          trace_tag=trace_tag,
                          trigger_instances=trigger_instances,
                          rules=rules,
                          action_executions=action_executions)
        return Trace.add_or_update(created)
