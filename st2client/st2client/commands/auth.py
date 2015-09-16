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

import getpass
import json
import logging

from st2client import models
from st2client.commands import resource
from st2client.commands.noop import NoopCommand
from st2client.exceptions.operations import OperationFailureException
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class TokenCreateCommand(resource.ResourceCommand):

    display_attributes = ['user', 'token', 'expiry']

    def __init__(self, resource, *args, **kwargs):

        kwargs['has_token_opt'] = False

        super(TokenCreateCommand, self).__init__(
            resource, kwargs.pop('name', 'create'),
            'Authenticate user and aquire access token.',
            *args, **kwargs)

        self.parser.add_argument('username',
                                 help='Name of the user to authenticate.')

        self.parser.add_argument('-p', '--password', dest='password',
                                 help='Password for the user. If password is not provided, '
                                      'it will be prompted.')
        self.parser.add_argument('-l', '--ttl', type=int, dest='ttl', default=None,
                                 help='The life span of the token in seconds. '
                                      'Max TTL configured by the admin supersedes this.')
        self.parser.add_argument('-t', '--only-token', action='store_true', dest='only_token',
                                 default=False,
                                 help='Only print token to the console on successful '
                                      'authentication.')

    def run(self, args, **kwargs):
        if not args.password:
            args.password = getpass.getpass()
        instance = self.resource(ttl=args.ttl) if args.ttl else self.resource()
        return self.manager.create(instance, auth=(args.username, args.password), **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)

        if args.only_token:
            print(instance.token)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=self.display_attributes, json=args.json)


class ApiKeyBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ApiKeyBranch, self).__init__(
            models.ApiKey, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': ApiKeyListCommand,
                'get': ApiKeyGetCommand,
                'create': ApiKeyCreateCommand,
                'update': NoopCommand,
                'delete': ApiKeyDeleteCommand
            })

        self.commands['enable'] = ApiKeyEnableCommand(self.resource, self.app, self.subparsers)
        self.commands['disable'] = ApiKeyDisableCommand(self.resource, self.app, self.subparsers)


class ApiKeyListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'user', 'metadata']

    def __init__(self, resource, *args, **kwargs):
        super(ApiKeyListCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-u', '--user', type=str,
                                 help='Only return ApiKeys belonging to the provided user')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        filters = {}
        filters['user'] = args.user
        filters.update(**kwargs)
        return self.manager.get_all(**filters)


class ApiKeyGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'user', 'metadata']

    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK


class ApiKeyCreateCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ApiKeyCreateCommand, self).__init__(
            resource, 'create', 'Create a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('-u', '--user', type=str,
                                 help='User for which to create API Keys.',
                                 default='')
        self.parser.add_argument('-m', '--metadata', type=json.loads,
                                 help='User for which to create API Keys.',
                                 default={})
        self.parser.add_argument('-k', '--only-key', action='store_true', dest='only_key',
                                 default=False,
                                 help='Only print API Key to the console on creation.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        data = {}
        if args.user:
            data['user'] = args.user
        if args.metadata:
            data['metadata'] = args.metadata
        instance = self.resource.deserialize(data)
        return self.manager.create(instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            if not instance:
                raise Exception('Server did not create instance.')
        except Exception as e:
            message = e.message or str(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)
        if args.only_key:
            print(instance.key)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json)


class ApiKeyDeleteCommand(resource.ResourceDeleteCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK


class ApiKeyEnableCommand(resource.ResourceEnableCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK


class ApiKeyDisableCommand(resource.ResourceDisableCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK

