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

from st2client.models import core
from st2client.models.action_alias import ActionAlias
from st2client.models.action_alias import ActionAliasMatch
from st2client.commands import resource
from st2client.formatters import table


__all__ = [
    'ActionAliasBranch',
    'ActionAliasMatchCommand',
    'ActionAliasExecuteCommand'
]


class ActionAliasBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionAliasBranch, self).__init__(
            ActionAlias, description, app, subparsers,
            parent_parser=parent_parser, read_only=False,
            commands={
                'list': ActionAliasListCommand,
                'get': ActionAliasGetCommand
            })

        self.commands['match'] = ActionAliasMatchCommand(
            self.resource, self.app, self.subparsers,
            add_help=True)
        self.commands['execute'] = ActionAliasExecuteCommand(
            self.resource, self.app, self.subparsers,
            add_help=True)


class ActionAliasListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']


class ActionAliasGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'action_ref', 'formats']


class ActionAliasMatchCommand(resource.ResourceCommand):
    display_attributes = ['name', 'description']

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasMatchCommand, self).__init__(
            resource, 'match',
            'Get the %s that match the command text.' %
            resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('match_text',
                                 metavar='command',
                                 help=('Get the %s that match the command text.' %
                                       resource.get_display_name().lower()))
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
        alias_match = ActionAliasMatch()
        alias_match.command = args.match_text

        match, _ = self.manager.match(alias_match, **kwargs)
        return [match]

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


class ActionAliasExecuteCommand(resource.ResourceCommand):
    display_attributes = ['name']

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasExecuteCommand, self).__init__(
            resource, 'execute',
            ('Execute the command text by finding a matching %s.' %
             resource.get_display_name().lower()), *args, **kwargs)

        self.parser.add_argument('command_text',
                                 metavar='command',
                                 help=('Execute the command text by finding a matching %s.' %
                                       resource.get_display_name().lower()))
        self.parser.add_argument('-u', '--user', type=str, default=None,
                                 help='User under which to run the action (admins only).')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        payload = core.Resource()
        payload.command = args.command_text
        payload.user = args.user
        payload.source_channel = 'cli'

        alias_execution_mgr = self.app.client.managers['ActionAliasExecution']
        execution = alias_execution_mgr.match_and_execute(payload)
        return execution

    def run_and_print(self, args, **kwargs):
        execution = self.run(args, **kwargs)
        print("Matching Action-alias: '%s'" % execution.actionalias['ref'])
        print("To get the results, execute:\n st2 execution get %s" %
              (execution.execution['id']))
