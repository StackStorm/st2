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
from st2client.utils.date import format_isodate_for_user_timezone


TRACE_ATTRIBUTE_DISPLAY_ORDER = ['id', 'trace_tag', 'action_executions', 'rules',
                                 'trigger_instances', 'start_timestamp']

TRACE_HEADER_DISPLAY_ORDER = ['id', 'trace_tag', 'start_timestamp']

TRACE_COMPONENT_DISPLAY_LABELS = ['id', 'type', 'ref', 'updated_at']

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
        options['yaml'] = args.yaml
        options['attribute_transform_functions'] = self.attribute_transform_functions

        formatter = execution_formatter.ExecutionResult

        self.print_output(trace, formatter, **options)

        # Everything should be printed if we are printing json.
        if args.json or args.yaml:
            return

        components = []
        if any(attr in args.attr for attr in TRIGGER_INSTANCE_DISPLAY_OPTIONS):
            components.extend([Resource(**{'id': trigger_instance['object_id'],
                                           'type': TriggerInstance._alias.lower(),
                                           'ref': trigger_instance['ref'],
                                           'updated_at': trigger_instance['updated_at']})
                               for trigger_instance in trace.trigger_instances])
        if any(attr in args.attr for attr in ['all', 'rules']):
            components.extend([Resource(**{'id': rule['object_id'],
                                           'type': Rule._alias.lower(),
                                           'ref': rule['ref'],
                                           'updated_at': rule['updated_at']})
                               for rule in trace.rules])
        if any(attr in args.attr for attr in ACTION_EXECUTION_DISPLAY_OPTIONS):
            components.extend([Resource(**{'id': execution['object_id'],
                                           'type': LiveAction._alias.lower(),
                                           'ref': execution['ref'],
                                           'updated_at': execution['updated_at']})
                               for execution in trace.action_executions])
        if components:
            components.sort(key=lambda resource: resource.updated_at)
            self.print_output(components, table.MultiColumnTable,
                              attributes=TRACE_COMPONENT_DISPLAY_LABELS,
                              json=args.json, yaml=args.yaml)


class TraceListCommand(resource.ResourceCommand, SingleTraceDisplayMixin):
    display_attributes = ['id', 'uid', 'trace_tag', 'start_timestamp']

    attribute_transform_functions = {
        'start_timestamp': format_isodate_for_user_timezone
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
                                 help=('List N most recent %s.' %
                                       resource.get_plural_display_name().lower()))
        self.parser.add_argument('-s', '--sort', type=str, dest='sort_order',
                                 default='descending',
                                 help=('Sort %s by start timestamp, '
                                       'asc|ascending (earliest first) '
                                       'or desc|descending (latest first)' %
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

        if args.sort_order:
            if args.sort_order in ['asc', 'ascending']:
                kwargs['sort_asc'] = True
            elif args.sort_order in ['desc', 'descending']:
                kwargs['sort_desc'] = True

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
                              json=args.json, yaml=args.yaml,
                              attribute_transform_functions=self.attribute_transform_functions)


class TraceGetCommand(resource.ResourceGetCommand, SingleTraceDisplayMixin):
    display_attributes = ['all']
    attribute_display_order = TRACE_ATTRIBUTE_DISPLAY_ORDER
    attribute_transform_functions = {
        'start_timestamp': format_isodate_for_user_timezone
    }

    pk_argument_name = 'id'

    def __init__(self, resource, *args, **kwargs):
        super(TraceGetCommand, self).__init__(resource, *args, **kwargs)

        # Causation chains
        self.causation_group = self.parser.add_mutually_exclusive_group()

        self.causation_group.add_argument('-e', '--execution',
                                          help='Execution to show causation chain.')
        self.causation_group.add_argument('-r', '--rule', help='Rule to show causation chain.')
        self.causation_group.add_argument('-g', '--trigger-instance',
                                          help='TriggerInstance to show causation chain.')

        # display filter group
        self.display_filter_group = self.parser.add_argument_group()

        self.display_filter_group.add_argument('--show-executions', action='store_true',
                                              help='Only show executions.')
        self.display_filter_group.add_argument('--show-rules', action='store_true',
                                              help='Only show rules.')
        self.display_filter_group.add_argument('--show-trigger-instances', action='store_true',
                                              help='Only show trigger instances.')
        self.display_filter_group.add_argument('-n', '--hide-noop-triggers', action='store_true',
                                              help='Hide noop trigger instances.')

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
        # First filter for causation chains
        trace = self._filter_trace_components(trace=trace, args=args)
        # next filter for display purposes
        trace = self._apply_display_filters(trace=trace, args=args)
        return self.print_trace_details(trace=trace, args=args)

    @staticmethod
    def _filter_trace_components(trace, args):
        """
        This function walks up the component causal chain. It only returns
        properties in the causal chain and nothing else.
        """
        # check if any filtering is desired
        if not (args.execution or args.rule or args.trigger_instance):
            return trace

        component_id = None
        component_type = None

        # pick the right component type
        if args.execution:
            component_id = args.execution
            component_type = 'action_execution'
        elif args.rule:
            component_id = args.rule
            component_type = 'rule'
        elif args.trigger_instance:
            component_id = args.trigger_instance
            component_type = 'trigger_instance'

        # Initialize collection to use
        action_executions = []
        rules = []
        trigger_instances = []

        # setup flag to properly manage termination conditions
        search_target_found = component_id and component_type

        while search_target_found:
            components_list = []
            if component_type == 'action_execution':
                components_list = trace.action_executions
                to_update_list = action_executions
            elif component_type == 'rule':
                components_list = trace.rules
                to_update_list = rules
            elif component_type == 'trigger_instance':
                components_list = trace.trigger_instances
                to_update_list = trigger_instances
            # Look for search_target in the right collection and
            # once found look up the caused_by to keep movig up
            # the chain.
            search_target_found = False
            # init to default value
            component_caused_by_id = None
            for component in components_list:
                test_id = component['object_id']
                if test_id == component_id:
                    caused_by = component.get('caused_by', {})
                    component_id = caused_by.get('id', None)
                    component_type = caused_by.get('type', None)
                    # If provided the component_caused_by_id must match as well. This is mostly
                    # applicable for rules since the same rule may appear multiple times and can
                    # only be distinguished by causing TriggerInstance.
                    if component_caused_by_id and component_caused_by_id != component_id:
                        continue
                    component_caused_by_id = None
                    to_update_list.append(component)
                    # In some cases the component_id and the causing component are combined to
                    # provide the complete causation chain. Think rule + triggerinstance
                    if component_id and ':' in component_id:
                        component_id_split = component_id.split(':')
                        component_id = component_id_split[0]
                        component_caused_by_id = component_id_split[1]
                    search_target_found = True
                    break

        trace.action_executions = action_executions
        trace.rules = rules
        trace.trigger_instances = trigger_instances
        return trace

    @staticmethod
    def _apply_display_filters(trace, args):
        """
        This function looks at the disaply filters to determine which components
        should be displayed.
        """
        # If all the filters are false nothing is to be filtered.
        all_component_types = not(args.show_executions or
                                  args.show_rules or
                                  args.show_trigger_instances)

        # check if noop_triggers are to be hidden. This check applies whenever TriggerInstances
        # are to be shown.
        if (all_component_types or args.show_trigger_instances) and args.hide_noop_triggers:
            filtered_trigger_instances = []
            for trigger_instance in trace.trigger_instances:
                is_noop_trigger_instance = True
                for rule in trace.rules:
                    caused_by_id = rule.get('caused_by', {}).get('id', None)
                    if caused_by_id == trigger_instance['object_id']:
                        is_noop_trigger_instance = False
                if not is_noop_trigger_instance:
                    filtered_trigger_instances.append(trigger_instance)
            trace.trigger_instances = filtered_trigger_instances

        if all_component_types:
            return trace

        if not args.show_executions:
            trace.action_executions = []

        if not args.show_rules:
            trace.rules = []

        if not args.show_trigger_instances:
            trace.trigger_instances = []

        return trace
