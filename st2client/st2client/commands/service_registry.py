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

from st2client.models.service_registry import ServiceRegistryGroup
from st2client.models.service_registry import ServiceRegistryMember
from st2client import commands
from st2client.commands.noop import NoopCommand
from st2client.commands import resource


class ServiceRegistryBranch(commands.Branch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ServiceRegistryBranch, self).__init__(
            'service-registry', description,
            app, subparsers, parent_parser=parent_parser)

        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing service registry.'))

        # Instantiate commands
        args_groups = ['Manage service registry groups', self.app, self.subparsers]
        args_members = ['Manage service registry members', self.app, self.subparsers]

        self.commands['groups'] = ServiceRegistryGroupsBranch(*args_groups)
        self.commands['members'] = ServiceRegistryMembersBranch(*args_members)


class ServiceRegistryGroupsBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ServiceRegistryGroupsBranch, self).__init__(
            ServiceRegistryGroup, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': ServiceRegistryListGroupsCommand,
                'get': NoopCommand
            })

        del self.commands['get']


class ServiceRegistryMembersBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ServiceRegistryMembersBranch, self).__init__(
            ServiceRegistryMember, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': ServiceRegistryListMembersCommand,
                'get': NoopCommand
            })

        del self.commands['get']


class ServiceRegistryListGroupsCommand(resource.ResourceListCommand):
    display_attributes = ['group_id']
    attribute_display_order = ['group_id']

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        manager = self.app.client.managers['ServiceRegistryGroups']

        groups = manager.list()
        return groups


class ServiceRegistryListMembersCommand(resource.ResourceListCommand):
    display_attributes = ['group_id', 'member_id', 'capabilities']
    attribute_display_order = ['group_id', 'member_id', 'capabilities']

    def __init__(self, resource, *args, **kwargs):
        super(ServiceRegistryListMembersCommand, self).__init__(
            resource, *args, **kwargs
        )

        self.parser.add_argument('--group-id', dest='group_id', default=None,
                                 help='If provided only retrieve members for the specified group.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        groups_manager = self.app.client.managers['ServiceRegistryGroups']
        members_manager = self.app.client.managers['ServiceRegistryMembers']

        # If group ID is provided only retrieve members for that group, otherwise retrieve members
        # for all groups
        if args.group_id:
            members = members_manager.list(args.group_id)
            return members
        else:
            groups = groups_manager.list()

            result = []
            for group in groups:
                members = members_manager.list(group.group_id)
                result.extend(members)

            return result
