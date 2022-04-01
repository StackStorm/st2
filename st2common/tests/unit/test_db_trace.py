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
import bson

from st2common.models.db.trace import TraceDB, TraceComponentDB
from st2common.persistence.trace import Trace

from st2tests.base import CleanDbTestCase
from six.moves import range


class TraceDBTest(CleanDbTestCase):
    def test_get(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            action_executions=[str(bson.ObjectId()) for _ in range(4)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(5)],
        )
        retrieved = Trace.get(id=saved.id)
        self.assertEqual(retrieved.id, saved.id, "Incorrect trace retrieved.")

    def test_query(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            action_executions=[str(bson.ObjectId()) for _ in range(4)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(5)],
        )
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEqual(len(retrieved), 1, "Should have 1 trace.")
        self.assertEqual(retrieved[0].id, saved.id, "Incorrect trace retrieved.")

        # Add another trace with same trace_tag and confirm that we support.
        # This is most likley an anti-pattern for the trace_tag but it is an unknown.
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            action_executions=[str(bson.ObjectId()) for _ in range(2)],
            rules=[str(bson.ObjectId()) for _ in range(4)],
            trigger_instances=[str(bson.ObjectId()) for _ in range(3)],
        )
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEqual(len(retrieved), 2, "Should have 2 traces.")

    def test_update(self):
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace", action_executions=[], rules=[], trigger_instances=[]
        )
        retrieved = Trace.query(trace_tag=saved.trace_tag)
        self.assertEqual(len(retrieved), 1, "Should have 1 trace.")
        self.assertEqual(retrieved[0].id, saved.id, "Incorrect trace retrieved.")

        no_action_executions = 4
        no_rules = 4
        no_trigger_instances = 5
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            id_=retrieved[0].id,
            action_executions=[
                str(bson.ObjectId()) for _ in range(no_action_executions)
            ],
            rules=[str(bson.ObjectId()) for _ in range(no_rules)],
            trigger_instances=[
                str(bson.ObjectId()) for _ in range(no_trigger_instances)
            ],
        )
        retrieved = Trace.query(trace_tag=saved.trace_tag)

        self.assertEqual(len(retrieved), 1, "Should have 1 trace.")
        self.assertEqual(retrieved[0].id, saved.id, "Incorrect trace retrieved.")
        # validate update
        self.assertEqual(
            len(retrieved[0].action_executions),
            no_action_executions,
            "Failed to update action_executions.",
        )
        self.assertEqual(len(retrieved[0].rules), no_rules, "Failed to update rules.")
        self.assertEqual(
            len(retrieved[0].trigger_instances),
            no_trigger_instances,
            "Failed to update trigger_instances.",
        )

    def test_update_via_list_push(self):
        no_action_executions = 4
        no_rules = 4
        no_trigger_instances = 5
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            action_executions=[
                str(bson.ObjectId()) for _ in range(no_action_executions)
            ],
            rules=[str(bson.ObjectId()) for _ in range(no_rules)],
            trigger_instances=[
                str(bson.ObjectId()) for _ in range(no_trigger_instances)
            ],
        )

        # push updates
        Trace.push_action_execution(
            saved, action_execution=TraceComponentDB(object_id=str(bson.ObjectId()))
        )
        Trace.push_rule(saved, rule=TraceComponentDB(object_id=str(bson.ObjectId())))
        Trace.push_trigger_instance(
            saved, trigger_instance=TraceComponentDB(object_id=str(bson.ObjectId()))
        )

        retrieved = Trace.get(id=saved.id)
        self.assertEqual(retrieved.id, saved.id, "Incorrect trace retrieved.")
        self.assertEqual(len(retrieved.action_executions), no_action_executions + 1)
        self.assertEqual(len(retrieved.rules), no_rules + 1)
        self.assertEqual(len(retrieved.trigger_instances), no_trigger_instances + 1)

    def test_update_via_list_push_components(self):
        no_action_executions = 4
        no_rules = 4
        no_trigger_instances = 5
        saved = TraceDBTest._create_save_trace(
            trace_tag="test_trace",
            action_executions=[
                str(bson.ObjectId()) for _ in range(no_action_executions)
            ],
            rules=[str(bson.ObjectId()) for _ in range(no_rules)],
            trigger_instances=[
                str(bson.ObjectId()) for _ in range(no_trigger_instances)
            ],
        )

        retrieved = Trace.push_components(
            saved,
            action_executions=[
                TraceComponentDB(object_id=str(bson.ObjectId()))
                for _ in range(no_action_executions)
            ],
            rules=[
                TraceComponentDB(object_id=str(bson.ObjectId()))
                for _ in range(no_rules)
            ],
            trigger_instances=[
                TraceComponentDB(object_id=str(bson.ObjectId()))
                for _ in range(no_trigger_instances)
            ],
        )

        self.assertEqual(retrieved.id, saved.id, "Incorrect trace retrieved.")
        self.assertEqual(len(retrieved.action_executions), no_action_executions * 2)
        self.assertEqual(len(retrieved.rules), no_rules * 2)
        self.assertEqual(len(retrieved.trigger_instances), no_trigger_instances * 2)

    @staticmethod
    def _create_save_trace(
        trace_tag, id_=None, action_executions=None, rules=None, trigger_instances=None
    ):

        if action_executions is None:
            action_executions = []
        action_executions = [
            TraceComponentDB(object_id=action_execution)
            for action_execution in action_executions
        ]

        if rules is None:
            rules = []
        rules = [TraceComponentDB(object_id=rule) for rule in rules]

        if trigger_instances is None:
            trigger_instances = []
        trigger_instances = [
            TraceComponentDB(object_id=trigger_instance)
            for trigger_instance in trigger_instances
        ]

        created = TraceDB(
            id=id_,
            trace_tag=trace_tag,
            trigger_instances=trigger_instances,
            rules=rules,
            action_executions=action_executions,
        )
        return Trace.add_or_update(created)
