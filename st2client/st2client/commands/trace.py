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

from st2client.models import Resource, Trace, TriggerInstance, Rule, LiveAction
from st2client.exceptions.operations import OperationFailureException
from st2client.formatters import table
from st2client.formatters import execution as execution_formatter
from st2client.commands import resource
from st2client.utils.date import format_isodate


TRACE_ATTRIBUTE_DISPLAY_ORDER = ['id', 'trace_tag', 'action_executions', 'rules',
                                 'trigger_instances', 'start_timestamp']

TRACE_HEADER_DISPLAY_ORDER = ['id', 'trace_tag', 'start_timestamp']

TRACE_COMPONENT_DISPLAY_LABELS = ['id', 'type', 'updated_at']

TRACE_DISPLAY_ATTRIBUTES = ['all']

TRIGGER_INSTANCE_DISPLAY_OPTIONS = [
    'all',
    'trigger-instances',
    'trigger_instances',
    'triggerinstances',
    'triggers'
]

ACTION_EXECUTION_DISPLAY_OPTIONS = [
    'all',
    'executions',
    'action-executions',
    'action_executions',
    'actionexecutions',
    'actions'
]


class TraceBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TraceBranch, self).__init__(
            Trace, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': TraceListCommand,
                'get': TraceGetCommand
            })


class SingleTraceDisplayMixin(object):

    def print_trace_details(self, trace, args, **kwargs):
        options = {'attributes': TRACE_ATTRIBUTE_DISPLAY_ORDER if args.json else
                   TRACE_HEADER_DISPLAY_ORDER}
        options['json'] = args.json
        options['attribute_transform_functions'] = self.attribute_transform_functions

        formatter = execution_formatter.ExecutionResult

        self.print_output(trace, formatter, **options)

        # Everything should be printed if we are printing json.
        if args.json:
            return

        components = []
        if any(attr in args.attr for attr in TRIGGER_INSTANCE_DISPLAY_OPTIONS):
            components.extend([Resource(**{'id': trigger_instance['object_id'],
                                           'type': TriggerInstance._alias.lower(),
                                           'updated_at': trigger_instance['updated_at']})
                               for trigger_instance in trace.trigger_instances])
        if any(attr in args.attr for attr in ['all', 'rules']):
            components.extend([Resource(**{'id': rule['object_id'],
                                           'type': Rule._alias.lower(),
                                           'updated_at': rule['updated_at']})
                               for rule in trace.rules])
        if any(attr in args.attr for attr in ACTION_EXECUTION_DISPLAY_OPTIONS):
            components.extend([Resource(**{'id': execution['object_id'],
                                           'type': LiveAction._alias.lower(),
                                           'updated_at': execution['updated_at']})
                               for execution in trace.action_executions])
        if components:
            components.sort(key=lambda resource: resource.updated_at)
            self.print_output(components, table.MultiColumnTable,
                              attributes=TRACE_COMPONENT_DISPLAY_LABELS,
                              json=args.json)


class TraceListCommand(resource.ResourceCommand, SingleTraceDisplayMixin):
    display_attributes = ['id', 'trace_tag', 'start_timestamp']

    attribute_transform_functions = {
        'start_timestamp': format_isodate
    }

    attribute_display_order = TRACE_ATTRIBUTE_DISPLAY_ORDER

    def __init__(self, resource, *args, **kwargs):
        super(TraceListCommand, self).__init__(
            resource, 'list', 'Get the list of the 50 most recent %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=50,
                                 help=('List N most recent %s; '
                                       'list all if 0.' %
                                       resource.get_plural_display_name().lower()))

        # Filter options
        self.group.add_argument('-c', '--trace-tag', help='Trace-tag to filter the list.')
        self.group.add_argument('-e', '--execution', help='Execution to filter the list.')
        self.group.add_argument('-r', '--rule', help='Rule to filter the list.')
        self.group.add_argument('-g', '--trigger-instance',
                                help='TriggerInstance to filter the list.')
        # Display options
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.trace_tag:
            kwargs['trace_tag'] = args.trace_tag
        if args.trigger_instance:
            kwargs['trigger_instance'] = args.trigger_instance
        if args.execution:
            kwargs['execution'] = args.execution
        if args.rule:
            kwargs['rule'] = args.rule

        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        if instances and len(instances) == 1:
            # For a single Trace we must include the components unless
            # user has overriden the attributes to display
            if args.attr == self.display_attributes:
                args.attr = ['all']
            self.print_trace_details(trace=instances[0], args=args)
        else:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json,
                              attribute_transform_functions=self.attribute_transform_functions)


class TraceGetCommand(resource.ResourceGetCommand, SingleTraceDisplayMixin):
    display_attributes = ['all']
    attribute_display_order = TRACE_ATTRIBUTE_DISPLAY_ORDER
    attribute_transform_functions = {
        'start_timestamp': format_isodate
    }

    pk_argument_name = 'id'

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        return self.get_resource_by_id(resource_id, **kwargs)

    @resource.add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        trace = None
        try:
            trace = self.run(args, **kwargs)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)
            raise OperationFailureException('Trace %s not found.' % (args.id))
        return self.print_trace_details(trace=trace, args=args)
