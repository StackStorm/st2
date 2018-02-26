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

from st2client import models
from st2client.commands import resource
from st2client.formatters import table
from st2client.utils.date import format_isodate_for_user_timezone


class RuleEnforcementBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(RuleEnforcementBranch, self).__init__(
            models.RuleEnforcement, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': RuleEnforcementListCommand,
                'get': RuleEnforcementGetCommand,
            })


class RuleEnforcementGetCommand(resource.ResourceGetCommand):
    display_attributes = ['id', 'rule.ref', 'trigger_instance_id',
                          'execution_id', 'failure_reason', 'enforced_at']
    attribute_display_order = ['id', 'rule.ref', 'trigger_instance_id',
                               'execution_id', 'failure_reason', 'enforced_at']

    pk_argument_name = 'id'

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        return self.get_resource_by_id(resource_id, **kwargs)


class RuleEnforcementListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'rule.ref', 'trigger_instance_id',
                          'execution_id', 'enforced_at']
    attribute_display_order = ['id', 'rule.ref', 'trigger_instance_id',
                               'execution_id', 'enforced_at']

    attribute_transform_functions = {
        'enforced_at': format_isodate_for_user_timezone
    }

    def __init__(self, resource, *args, **kwargs):

        self.default_limit = 50

        super(RuleEnforcementListCommand, self).__init__(
            resource, 'list', 'Get the list of the %s most recent %s.' %
            (self.default_limit, resource.get_plural_display_name().lower()),
            *args, **kwargs)
        self.resource_name = resource.get_plural_display_name().lower()
        self.group = self.parser.add_argument_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=self.default_limit,
                                 help=('List N most recent %s. Use -n -1 to fetch the full result \
                                       set.' % self.resource_name))

        # Filter options
        self.group.add_argument('--trigger-instance',
                                help='Trigger instance id to filter the list.')

        self.group.add_argument('--execution',
                                help='Execution id to filter the list.')
        self.group.add_argument('--rule',
                                help='Rule ref to filter the list.')

        self.parser.add_argument('-tg', '--timestamp-gt', type=str, dest='timestamp_gt',
                                 default=None,
                                 help=('Only return enforcements with enforced_at '
                                       'greater than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))
        self.parser.add_argument('-tl', '--timestamp-lt', type=str, dest='timestamp_lt',
                                 default=None,
                                 help=('Only return enforcements with enforced_at '
                                       'lower than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))
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
        if args.trigger_instance:
            kwargs['trigger_instance'] = args.trigger_instance
        if args.execution:
            kwargs['execution'] = args.execution
        if args.rule:
            kwargs['rule_ref'] = args.rule
        if args.timestamp_gt:
            kwargs['enforced_at_gt'] = args.timestamp_gt
        if args.timestamp_lt:
            kwargs['enforced_at_lt'] = args.timestamp_lt

        return self.manager.query_with_count(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances, count = self.run(args, **kwargs)
        if args.json or args.yaml:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml,
                              attribute_transform_functions=self.attribute_transform_functions)
        else:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width)
            if args.last and count and count > args.last:
                table.SingleRowTable.note_box(self.resource_name, args.last)
