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

from st2client.formatters import table
from st2client.commands import resource
from st2client.models.rbac import Role
from st2client.models.rbac import UserRoleAssignment

__all__ = [
    'RoleBranch',
    'RoleAssignmentBranch'
]

ROLE_ATTRIBUTE_DISPLAY_ORDER = ['id', 'name', 'system', 'permission_grants']
ROLE_ASSIGNMENT_ATTRIBUTE_DISPLAY_ORDER = ['id', 'role', 'user', 'is_remote', 'description']


class RoleBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(RoleBranch, self).__init__(
            Role, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': RoleListCommand,
                'get': RoleGetCommand
            })


class RoleListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'name', 'system', 'description']
    attribute_display_order = ROLE_ATTRIBUTE_DISPLAY_ORDER

    def __init__(self, resource, *args, **kwargs):
        super(RoleListCommand, self).__init__(
            resource, 'list', 'Get the list of the  %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()

        # Filter options
        self.group.add_argument('-s', '--system', action='store_true',
                                help='Only display system roles.')

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
        if args.system:
            kwargs['system'] = args.system

        if args.system:
            result = self.manager.query(**kwargs)
        else:
            result = self.manager.get_all(**kwargs)

        return result

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


class RoleGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ROLE_ATTRIBUTE_DISPLAY_ORDER
    pk_argument_name = 'id'


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
    display_attributes = ['id', 'role', 'user', 'is_remote', 'source', 'description']
    attribute_display_order = ROLE_ASSIGNMENT_ATTRIBUTE_DISPLAY_ORDER

    def __init__(self, resource, *args, **kwargs):
        super(RoleAssignmentListCommand, self).__init__(
            resource, 'list', 'Get the list of the  %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        # Filter options
        self.parser.add_argument('-r', '--role', help='Role to filter on.')
        self.parser.add_argument('-u', '--user', help='User to filter on.')
        self.parser.add_argument('-s', '--source', help='Source to filter on.')
        self.parser.add_argument('--remote', action='store_true',
                                help='Only display remote role assignments.')

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
        if args.source:
            kwargs['source'] = args.source
        if args.remote:
            kwargs['remote'] = args.remote

        if args.role or args.user or args.remote or args.source:
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
    attribute_display_order = ROLE_ASSIGNMENT_ATTRIBUTE_DISPLAY_ORDER
    pk_argument_name = 'id'
