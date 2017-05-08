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

from st2client.exceptions.operations import OperationFailureException
from st2client.formatters import table
from st2client.commands import resource
from st2client.models.rbac import UserRoleAssignment

__all__ = [
    'RoleAssignmentBranch'
]

ATTRIBUTE_DISPLAY_ORDER = ['id', 'role', 'user', 'is_remote', 'description']


class RoleAssignmentBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(RoleAssignmentBranch, self).__init__(
            UserRoleAssignment, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': RoleAssignmentListCommand,
                'get': RoleAssignmentGetCommand
            })


class RoleAssignmentListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'role', 'user', 'is_remote', 'description']
    attribute_display_order = ATTRIBUTE_DISPLAY_ORDER

    def __init__(self, resource, *args, **kwargs):
        super(RoleAssignmentListCommand, self).__init__(
            resource, 'list', 'Get the list of the  %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()

        # Filter options
        self.group.add_argument('-r', '--role', help='Role to filter on.')
        self.group.add_argument('-u', '--user', help='User to filter on.')

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
        if args.role:
            kwargs['role'] = args.role
        if args.user:
            kwargs['user'] = args.user

        if args.role or args.user:
            result = self.manager.query(**kwargs)
        else:
            result = self.manager.get_all(**kwargs)

        return result

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


class RoleAssignmentGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ATTRIBUTE_DISPLAY_ORDER
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
