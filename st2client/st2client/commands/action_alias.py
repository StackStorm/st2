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

from st2common.exceptions.actionalias import ActionAliasAmbiguityException
from st2common.models.utils.action_alias_utils import extract_parameters_for_action_alias_db
from st2common.util.actionalias_matching import match_command_to_alias

from st2client import models
from st2client.models.action_alias import ActionAlias
from st2client.models.action import LiveAction

from st2client.commands import resource
from st2client.formatters import table

__all__ = [
    'ActionAliasBranch'
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
            add_help=False)
        self.commands['execute'] = ActionAliasExecuteCommand(
            LiveAction, self.app, self.subparsers,
            add_help=False)


class ActionAliasListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']


class ActionAliasGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'action_ref', 'formats']


class ActionAliasMatchCommand(resource.ResourceCommand):
    display_attributes = ['id', 'name', 'description']

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasMatchCommand, self).__init__(
            resource, 'match',
            'Get the list of %s that match the command text.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('match_text',
                                 metavar='command',
                                 help=help)

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
        aliases = self.manager.get_all(**kwargs)
        matches = match_command_to_alias(args.match_text, aliases)
        return [match[0] for match in matches]  # show only alias objects

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


class ActionAliasExecuteCommand(resource.ResourceCommand):
    display_attributes = ['id', 'name', 'description']

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasExecuteCommand, self).__init__(
            resource, 'execute',
            'Execute the command text by finding a matching ActionAlias.',
            *args, **kwargs)

        self.parser.add_argument('command_text',
                                 metavar='command',
                                 help=help)
        self.parser.add_argument('--trace-tag', '--trace_tag',
                                 help='A trace tag string to track execution later.',
                                 dest='trace_tag', required=False)
        self.parser.add_argument('--trace-id',
                                 help='Existing trace id for this execution.',
                                 dest='trace_id', required=False)
        self.parser.add_argument('-a', '--async',
                                 action='store_true', dest='async',
                                 help='Do not wait for action to finish.')
        self.parser.add_argument('-u', '--user', type=str, default=None,
                                 help='User under which to run the action (admins only).')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        aliases = self.manager.get_all(**kwargs)
        matches = match_command_to_alias(args.command_text, aliases)
        if len(matches) > 1:
            raise ActionAliasAmbiguityException("Too many matches for provided command",
                                                matches=matches)
        elif len(matches) == 0:
            raise ActionAliasAmbiguityException("Could not locate an ActionAlias with a "
                                                "matching format command", matches=matches)
        match = matches[0]
        action_alias_db = match[0]

        if not action_alias_db.enabled:
            raise ValueError('Action alias with name "%s" is disabled.' %
                             (action_alias_db.ref))

        execution_parameters = extract_parameters_for_action_alias_db(
            action_alias_db=action_alias_db,
            format_str=matches[2],
            param_stream=args.command_text)

        execution = models.LiveAction()
        execution.action = action_alias_db.action_ref
        execution.parameters = execution_parameters
        execution.user = args.user

        if not args.trace_id and args.trace_tag:
            execution.context = {'trace_context': {'trace_tag': args.trace_tag}}

        if args.trace_id:
            execution.context = {'trace_context': {'id_': args.trace_id}}

        action_exec_mgr = self.app.client.managers['LiveAction']

        execution = action_exec_mgr.create(execution, **kwargs)
        execution = self._get_execution_result(execution=execution,
                                               action_exec_mgr=action_exec_mgr,
                                               args=args, **kwargs)
        return execution

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)
