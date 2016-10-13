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

from st2client.commands import resource
from st2client.models import TriggerType
from st2client.formatters import table


class TriggerTypeBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerTypeBranch, self).__init__(
            TriggerType, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': TriggerTypeListCommand,
                'get': TriggerTypeGetCommand,
                'update': TriggerTypeUpdateCommand,
                'delete': TriggerTypeDeleteCommand
            })

        # Registers extended commands
        self.commands['getspecs'] = TriggerTypeSubTriggerCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class TriggerTypeListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description']


class TriggerTypeGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'parameters_schema', 'payload_schema']


class TriggerTypeUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class TriggerTypeDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass


class TriggerTypeSubTriggerCommand(resource.ResourceCommand):
    attribute_display_order = ['id', 'ref', 'context', 'parameters', 'status',
                               'start_timestamp', 'result']

    def __init__(self, resource, *args, **kwargs):

        super(TriggerTypeSubTriggerCommand, self).__init__(
            resource, kwargs.pop('name', 'getspecs'),
            'A command to return Trigger Specifications of a Trigger.',
            *args, **kwargs)

        self.parser.add_argument('ref', nargs='?',
                                 metavar='ref',
                                 help='Fully qualified name (pack.trigger_name) ' +
                                 'of the trigger.')

        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        trigger_mgr = self.app.client.managers['Trigger']
        return trigger_mgr.query(**{'type': args.ref})

    @resource.add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        if args.help:
            self.parser.print_help()
            return
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          json=args.json, yaml=args.yaml)
