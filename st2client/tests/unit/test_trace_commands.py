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

from __future__ import absolute_import
import argparse

from tests import base

from st2client.commands import trace as trace_commands
from st2client.models import trace as trace_models


class TraceCommandTestCase(base.BaseCLITestCase):

    def test_trace_get_filter_trace_components_executions(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions',
                [{'object_id': 'e1', 'caused_by': {'id': 'r1:t1', 'type': 'rule'}}])
        setattr(trace, 'rules',
                [{'object_id': 'r1', 'caused_by': {'id': 't1', 'type': 'trigger_instance'}}])
        setattr(trace, 'trigger_instances',
                [{'object_id': 't1', 'caused_by': {}},
                 {'object_id': 't2', 'caused_by': {'id': 'e1', 'type': 'execution'}}])

        args = argparse.Namespace()
        setattr(args, 'execution', 'e1')
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._filter_trace_components(trace, args)
        self.assertEquals(len(trace.action_executions), 1)
        self.assertEquals(len(trace.rules), 1)
        self.assertEquals(len(trace.trigger_instances), 1)

    def test_trace_get_filter_trace_components_rules(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions',
                [{'object_id': 'e1', 'caused_by': {'id': 'r1:t1', 'type': 'rule'}}])
        setattr(trace, 'rules',
                [{'object_id': 'r1', 'caused_by': {'id': 't1', 'type': 'trigger_instance'}}])
        setattr(trace, 'trigger_instances',
                [{'object_id': 't1', 'caused_by': {}},
                 {'object_id': 't2', 'caused_by': {'id': 'e1', 'type': 'execution'}}])

        args = argparse.Namespace()
        setattr(args, 'execution', None)
        setattr(args, 'rule', 'r1')
        setattr(args, 'trigger_instance', None)
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._filter_trace_components(trace, args)
        self.assertEquals(len(trace.action_executions), 0)
        self.assertEquals(len(trace.rules), 1)
        self.assertEquals(len(trace.trigger_instances), 1)

    def test_trace_get_filter_trace_components_trigger_instances(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions',
                [{'object_id': 'e1', 'caused_by': {'id': 'r1:t1', 'type': 'rule'}}])
        setattr(trace, 'rules',
                [{'object_id': 'r1', 'caused_by': {'id': 't1', 'type': 'trigger_instance'}}])
        setattr(trace, 'trigger_instances',
                [{'object_id': 't1', 'caused_by': {}},
                 {'object_id': 't2', 'caused_by': {'id': 'e1', 'type': 'execution'}}])

        args = argparse.Namespace()
        setattr(args, 'execution', None)
        setattr(args, 'rule', None)
        setattr(args, 'trigger_instance', 't1')
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._filter_trace_components(trace, args)
        self.assertEquals(len(trace.action_executions), 0)
        self.assertEquals(len(trace.rules), 0)
        self.assertEquals(len(trace.trigger_instances), 1)

    def test_trace_get_apply_display_filters_show_executions(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions', ['1'])
        setattr(trace, 'rules', ['1'])
        setattr(trace, 'trigger_instances', ['1'])

        args = argparse.Namespace()
        setattr(args, 'show_executions', True)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertTrue(trace.action_executions)
        self.assertFalse(trace.rules)
        self.assertFalse(trace.trigger_instances)

    def test_trace_get_apply_display_filters_show_rules(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions', ['1'])
        setattr(trace, 'rules', ['1'])
        setattr(trace, 'trigger_instances', ['1'])

        args = argparse.Namespace()
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', True)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertFalse(trace.action_executions)
        self.assertTrue(trace.rules)
        self.assertFalse(trace.trigger_instances)

    def test_trace_get_apply_display_filters_show_trigger_instances(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions', ['1'])
        setattr(trace, 'rules', ['1'])
        setattr(trace, 'trigger_instances', ['1'])

        args = argparse.Namespace()
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', True)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertFalse(trace.action_executions)
        self.assertFalse(trace.rules)
        self.assertTrue(trace.trigger_instances)

    def test_trace_get_apply_display_filters_show_multiple(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions', ['1'])
        setattr(trace, 'rules', ['1'])
        setattr(trace, 'trigger_instances', ['1'])

        args = argparse.Namespace()
        setattr(args, 'show_executions', True)
        setattr(args, 'show_rules', True)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertTrue(trace.action_executions)
        self.assertTrue(trace.rules)
        self.assertFalse(trace.trigger_instances)

    def test_trace_get_apply_display_filters_show_all(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions', ['1'])
        setattr(trace, 'rules', ['1'])
        setattr(trace, 'trigger_instances', ['1'])

        args = argparse.Namespace()
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', False)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertEquals(len(trace.action_executions), 1)
        self.assertEquals(len(trace.rules), 1)
        self.assertEquals(len(trace.trigger_instances), 1)

    def test_trace_get_apply_display_filters_hide_noop(self):
        trace = trace_models.Trace()
        setattr(trace, 'action_executions',
                [{'object_id': 'e1', 'caused_by': {'id': 'r1:t1', 'type': 'rule'}}])
        setattr(trace, 'rules',
                [{'object_id': 'r1', 'caused_by': {'id': 't1', 'type': 'trigger_instance'}}])
        setattr(trace, 'trigger_instances',
                [{'object_id': 't1', 'caused_by': {}},
                 {'object_id': 't2', 'caused_by': {'id': 'e1', 'type': 'execution'}}])

        args = argparse.Namespace()
        setattr(args, 'show_executions', False)
        setattr(args, 'show_rules', False)
        setattr(args, 'show_trigger_instances', False)
        setattr(args, 'hide_noop_triggers', True)

        trace = trace_commands.TraceGetCommand._apply_display_filters(trace, args)
        self.assertEquals(len(trace.action_executions), 1)
        self.assertEquals(len(trace.rules), 1)
        self.assertEquals(len(trace.trigger_instances), 1)
