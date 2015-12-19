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

from st2client import models
from st2client.commands import resource


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


class RuleListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']
    display_attributes_iftt = ['ref', 'trigger.ref', 'action.ref', 'enabled']

    def __init__(self, resource, *args, **kwargs):
        super(RuleListCommand, self).__init__(resource, *args, **kwargs)

        self.group = self.parser.add_argument_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=50,
                                 help=('List N most recent %s; '
                                       'list all if 0.' %
                                       resource.get_plural_display_name().lower()))
        self.parser.add_argument('--iftt', action='store_true',
                                 help='Show trigger and action in display list.')
        self.group.add_argument('-c', '--action',
                                help='Action reference to filter the list.')
        self.group.add_argument('-g', '--trigger',
                                help='Trigger type reference to filter the list.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.action:
            kwargs['action'] = args.action
        if args.trigger:
            kwargs['trigger'] = args.trigger
        if args.iftt:
            # switch attr to display the trigger and action
            args.attr = self.display_attributes_iftt

        return self.manager.query(limit=args.last, **kwargs)


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
