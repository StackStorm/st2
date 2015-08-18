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

from st2client.models import Trace
from st2client.formatters import table
from st2client.commands import resource
from st2client.utils.date import format_isodate


TRACE_ATTRIBUTE_DISPLAY_ORDER = ['id', 'trace_id', 'action_executions', 'rules',
                                 'triggerinstances', 'start_timestamp']

TRACE_DISPLAY_ATTRIBUTES = ['all']


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


class TraceListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'trace_id', 'start_timestamp']

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
        self.group.add_argument('-i', '--trace-id', help='Trace-id to filter the list.')
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
        if args.trace_id:
            kwargs['trace_id'] = args.trace_id
        if args.trigger_instance:
            kwargs['trigger_instance'] = args.trigger_instance
        if args.execution:
            kwargs['action_execution'] = args.execution
        if args.rule:
            kwargs['rule'] = args.rule

        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        if instances and len(instances) == 1:
            # If there is an attribute override from the CLI use that value else
            # use TRACE_DISPLAY_ATTRIBUTES as those are preferred for a single trace.
            attributes = args.attr
            if args.attr == self.display_attributes:
                attributes = TRACE_DISPLAY_ATTRIBUTES
            self.print_output(instances[0], table.PropertyValueTable,
                              attributes=attributes, json=args.json,
                              attribute_display_order=self.attribute_display_order)
        else:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json,
                              attribute_transform_functions=self.attribute_transform_functions)


class TraceGetCommand(resource.ResourceGetCommand):
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
