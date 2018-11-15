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


class RuleBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(RuleBranch, self).__init__(
            models.Rule, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': RuleListCommand,
                'get': RuleGetCommand,
                'update': RuleUpdateCommand,
                'delete': RuleDeleteCommand
            })

        self.commands['enable'] = RuleEnableCommand(self.resource, self.app, self.subparsers)
        self.commands['disable'] = RuleDisableCommand(self.resource, self.app, self.subparsers)


class RuleListCommand(resource.ResourceTableCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']
    display_attributes_iftt = ['ref', 'trigger.ref', 'action.ref', 'enabled']

    def __init__(self, resource, *args, **kwargs):

        self.default_limit = 50

        super(RuleListCommand, self).__init__(resource, 'list',
                                              'Get the list of the %s most recent %s.' %
                                              (self.default_limit,
                                               resource.get_plural_display_name().lower()),
                                              *args, **kwargs)

        self.resource_name = resource.get_plural_display_name().lower()
        self.group = self.parser.add_argument_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=self.default_limit,
                                 help=('List N most recent %s. Use -n -1 to fetch the full result \
                                       set.' % self.resource_name))
        self.parser.add_argument('--iftt', action='store_true',
                                 help='Show trigger and action in display list.')
        self.parser.add_argument('-p', '--pack', type=str,
                                 help=('Only return resources belonging to the'
                                       ' provided pack'))
        self.group.add_argument('-c', '--action',
                                help='Action reference to filter the list.')
        self.group.add_argument('-g', '--trigger',
                                help='Trigger type reference to filter the list.')
        self.enabled_filter_group = self.parser.add_mutually_exclusive_group()
        self.enabled_filter_group.add_argument('--enabled', action='store_true',
                                               help='Show rules that are enabled.')
        self.enabled_filter_group.add_argument('--disabled', action='store_true',
                                               help='Show rules that are disabled.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.pack:
            kwargs['pack'] = args.pack
        if args.action:
            kwargs['action'] = args.action
        if args.trigger:
            kwargs['trigger'] = args.trigger
        if args.enabled:
            kwargs['enabled'] = True
        if args.disabled:
            kwargs['enabled'] = False
        if args.iftt:
            # switch attr to display the trigger and action
            args.attr = self.display_attributes_iftt

        include_attributes = self._get_include_attributes(args=args)
        if include_attributes:
            include_attributes = ','.join(include_attributes)
            kwargs['params'] = {'include_attributes': include_attributes}

        return self.manager.query_with_count(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances, count = self.run(args, **kwargs)
        if args.json or args.yaml:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml)
        else:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width)

            if args.last and count and count > args.last:
                table.SingleRowTable.note_box(self.resource_name, args.last)


class RuleGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'uid', 'ref', 'pack', 'name', 'description',
                               'enabled']


class RuleUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class RuleEnableCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'description',
                               'enabled']


class RuleDisableCommand(resource.ContentPackResourceDisableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'description',
                               'enabled']


class RuleDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass
