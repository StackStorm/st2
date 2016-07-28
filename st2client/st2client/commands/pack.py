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
from st2client.commands.noop import NoopCommand
from st2client.formatters import table
from st2client.exceptions.operations import OperationFailureException


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


class PackListCommand(resource.ResourceListCommand):
    display_attributes = ['name', 'description', 'version', 'author']
    attribute_display_order = ['name', 'description', 'version', 'author']


class PackInstallCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackInstallCommand, self).__init__(resource, 'install',
            'Install a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the %s to install.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.install(args.name, **kwargs)


class PackRemoveCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRemoveCommand, self).__init__(resource, 'remove',
            'Remove a %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the %s to remove.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.remove(args.name, **kwargs)


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

        self.parser.add_argument('name',
                                 help='Name of the %s to register.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.register(args.name, **kwargs)


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
