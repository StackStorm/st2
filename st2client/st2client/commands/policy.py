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

import logging

from st2client import models
from st2client.commands import resource


LOG = logging.getLogger(__name__)


class PolicyTypeBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PolicyTypeBranch, self).__init__(
            models.PolicyType, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': PolicyTypeListCommand,
                'get': PolicyTypeGetCommand
            })


class PolicyTypeListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'resource_type', 'name', 'description']

    def __init__(self, resource, *args, **kwargs):
        super(PolicyTypeListCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-r', '--resource-type', type=str, dest='resource_type',
                                 help='Return policy types for the resource type.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if args.resource_type:
            filters = {'resource_type': args.resource_type}
            filters.update(**kwargs)
            return self.manager.query(**filters)
        else:
            return self.manager.get_all(**kwargs)


class PolicyTypeGetCommand(resource.ResourceGetCommand):
    pk_argument_name = 'ref_or_id'

    def get_resource(self, ref_or_id, **kwargs):
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)


class PolicyBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PolicyBranch, self).__init__(
            models.Policy, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': PolicyListCommand,
                'get': PolicyGetCommand,
                'update': PolicyUpdateCommand,
                'delete': PolicyDeleteCommand
            })


class PolicyListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'resource_ref', 'policy_type', 'enabled']

    def __init__(self, resource, *args, **kwargs):
        super(PolicyListCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-r', '--resource-ref', type=str, dest='resource_ref',
                                 help='Return policies for the resource ref.')
        self.parser.add_argument('-pt', '--policy-type', type=str, dest='policy_type',
                                 help='Return policies of the policy type.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if args.resource_ref or args.policy_type:
            filters = {}

            if args.resource_ref:
                filters['resource_ref'] = args.resource_ref

            if args.policy_type:
                filters['policy_type'] = args.policy_type

            filters.update(**kwargs)

            return self.manager.query(**filters)
        else:
            return self.manager.get_all(**kwargs)


class PolicyGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'resource_ref', 'policy_type',
                               'parameters']


class PolicyUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class PolicyDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass
