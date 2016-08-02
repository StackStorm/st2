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

from st2client.models import Pack
from st2client.commands import resource
from st2client.commands.action import ActionRunCommandMixin
from st2client.commands.noop import NoopCommand
from st2client.formatters import table
from st2client.exceptions.operations import OperationFailureException
from st2client.utils.color import format_status
import st2client.utils.terminal as term


LIVEACTION_STATUS_REQUESTED = 'requested'
LIVEACTION_STATUS_SCHEDULED = 'scheduled'
LIVEACTION_STATUS_DELAYED = 'delayed'
LIVEACTION_STATUS_RUNNING = 'running'
LIVEACTION_STATUS_SUCCEEDED = 'succeeded'
LIVEACTION_STATUS_FAILED = 'failed'
LIVEACTION_STATUS_TIMED_OUT = 'timeout'
LIVEACTION_STATUS_ABANDONED = 'abandoned'
LIVEACTION_STATUS_CANCELING = 'canceling'
LIVEACTION_STATUS_CANCELED = 'canceled'

LIVEACTION_COMPLETED_STATES = [
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
    LIVEACTION_STATUS_TIMED_OUT,
    LIVEACTION_STATUS_CANCELED,
    LIVEACTION_STATUS_ABANDONED
]


class PackBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PackBranch, self).__init__(
            Pack, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': PackListCommand,
                'get': NoopCommand
            })

        self.commands['register'] = PackRegisterCommand(self.resource, self.app, self.subparsers)
        self.commands['create'] = PackCreateCommand(self.resource, self.app, self.subparsers)
        self.commands['install'] = PackInstallCommand(self.resource, self.app, self.subparsers)
        self.commands['remove'] = PackRemoveCommand(self.resource, self.app, self.subparsers)
        self.commands['search'] = PackSearchCommand(self.resource, self.app, self.subparsers)


class PackResourceCommand(resource.ResourceCommand):
    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            if not instance:
                raise Exception('Server did not create instance.')
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json, yaml=args.yaml)
        except Exception as e:
            message = e.message or str(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)


class PackAsyncCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        if not instance:
            raise Exception('Server did not create instance.')

        parent_id = instance.execution_id

        stream_mgr = self.app.client.managers['Stream']

        for execution in stream_mgr.listen(['st2.execution__create', 'st2.execution__update']):
            if execution['id'] == parent_id and execution['status'] in LIVEACTION_COMPLETED_STATES:
                break

            if execution.get('parent', None) == parent_id:
                status = execution['status']
                ref = execution['action']['ref']

                if status == LIVEACTION_STATUS_SCHEDULED:
                    term.write('\t[{:^20}] {}'.format(format_status(status), ref))
                if status == LIVEACTION_STATUS_RUNNING:
                    term.write('\t[{:^20}] {}'.format(format_status(status), ref), override=True)
                if status in LIVEACTION_COMPLETED_STATES:
                    term.write('\t[{:^20}] {}'.format(format_status(status), ref), override=True)

        term.write('\n')


class PackListCommand(resource.ResourceListCommand):
    display_attributes = ['name', 'description', 'version', 'author']
    attribute_display_order = ['name', 'description', 'version', 'author']


class PackInstallCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackInstallCommand, self).__init__(resource, 'install',
            'Install new %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s to install.' %
                                 resource.get_plural_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.install(args.packs, **kwargs)


class PackRemoveCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRemoveCommand, self).__init__(resource, 'remove',
            'Remove %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s to remove.' %
                                 resource.get_plural_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.remove(args.packs, **kwargs)


class PackCreateCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackCreateCommand, self).__init__(resource, 'create',
            'Create a template for a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the %s to create.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.create(args.name, **kwargs)


class PackRegisterCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRegisterCommand, self).__init__(resource, 'register',
              'Register a %s: sync all file changes with DB.' % resource.get_display_name().lower(),
              *args, **kwargs)

        self.parser.add_argument('--types',
                                 nargs='+',
                                 help='Name of the %s to register.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.register(args.types, **kwargs)


class PackSearchCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackSearchCommand, self).__init__(resource, 'search',
            'Search for a %s in the directory.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('query',
                                 help='Search query.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.search(args.query, **kwargs)
