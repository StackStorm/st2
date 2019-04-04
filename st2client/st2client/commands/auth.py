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

import getpass
import json
import logging
import os

import requests
import six
from six.moves.configparser import ConfigParser
from six.moves import http_client

from st2client.base import BaseCLIApp
from st2client import config_parser
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
            'Authenticate user and acquire access token.',
            *args, **kwargs)

        self.parser.add_argument('username',
                                 help='Name of the user to authenticate.')

        self.parser.add_argument('-p', '--password', dest='password',
                                 help='Password for the user. If password is not provided, '
                                      'it will be prompted for.')
        self.parser.add_argument('-l', '--ttl', type=int, dest='ttl', default=None,
                                 help='The life span of the token in seconds. '
                                      'Max TTL configured by the admin supersedes this.')
        self.parser.add_argument('-t', '--only-token', action='store_true', dest='only_token',
                                 default=False,
                                 help='On successful authentication, print only token to the '
                                      'console.')

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
                              attributes=self.display_attributes, json=args.json, yaml=args.yaml)


class LoginCommand(resource.ResourceCommand):
    display_attributes = ['user', 'token', 'expiry']

    def __init__(self, resource, *args, **kwargs):

        kwargs['has_token_opt'] = False

        super(LoginCommand, self).__init__(
            resource, kwargs.pop('name', 'create'),
            'Authenticate user, acquire access token, and update CLI config directory',
            *args, **kwargs)

        self.parser.add_argument('username',
                                 help='Name of the user to authenticate.')

        self.parser.add_argument('-p', '--password', dest='password',
                                 help='Password for the user. If password is not provided, '
                                      'it will be prompted for.')
        self.parser.add_argument('-l', '--ttl', type=int, dest='ttl', default=None,
                                 help='The life span of the token in seconds. '
                                      'Max TTL configured by the admin supersedes this.')
        self.parser.add_argument('-w', '--write-password', action='store_true', default=False,
                                 dest='write_password',
                                 help='Write the password in plain text to the config file '
                                      '(default is to omit it)')

    def run(self, args, **kwargs):

        if not args.password:
            args.password = getpass.getpass()
        instance = self.resource(ttl=args.ttl) if args.ttl else self.resource()

        cli = BaseCLIApp()

        # Determine path to config file
        try:
            config_file = cli._get_config_file_path(args)
        except ValueError:
            # config file not found in args or in env, defaulting
            config_file = config_parser.ST2_CONFIG_PATH

        # Retrieve token
        manager = self.manager.create(instance, auth=(args.username, args.password), **kwargs)
        cli._cache_auth_token(token_obj=manager)

        # Update existing configuration with new credentials
        config = ConfigParser()
        config.read(config_file)

        # Modify config (and optionally populate with password)
        if not config.has_section('credentials'):
            config.add_section('credentials')

        config.set('credentials', 'username', args.username)
        if args.write_password:
            config.set('credentials', 'password', args.password)
        else:
            # Remove any existing password from config
            config.remove_option('credentials', 'password')

        config_existed = os.path.exists(config_file)
        with open(config_file, 'w') as cfg_file_out:
            config.write(cfg_file_out)
        # If we created the config file, correct the permissions
        if not config_existed:
            os.chmod(config_file, 0o660)

        return manager

    def run_and_print(self, args, **kwargs):
        try:
            self.run(args, **kwargs)
        except Exception as e:
            if self.app.client.debug:
                raise

            raise Exception('Failed to log in as %s: %s' % (args.username, six.text_type(e)))

        print('Logged in as %s' % (args.username))

        if not args.write_password:
            # Note: Client can't depend and import from common so we need to hard-code this
            # default value
            token_expire_hours = 24

            print('')
            print('Note: You didn\'t use --write-password option so the password hasn\'t been '
                  'stored in the client config and you will need to login again in %s hours when '
                  'the auth token expires.' % (token_expire_hours))
            print('As an alternative, you can run st2 login command with the "--write-password" '
                  'flag, but keep it mind this will cause it to store the password in plain-text '
                  'in the client config file (~/.st2/config).')


class WhoamiCommand(resource.ResourceCommand):
    display_attributes = ['user', 'token', 'expiry']

    def __init__(self, resource, *args, **kwargs):

        kwargs['has_token_opt'] = False

        super(WhoamiCommand, self).__init__(
            resource, kwargs.pop('name', 'create'),
            'Display the currently authenticated user',
            *args, **kwargs)

    def run(self, args, **kwargs):
        user_info = self.app.client.get_user_info(**kwargs)
        return user_info

    def run_and_print(self, args, **kwargs):
        try:
            user_info = self.run(args, **kwargs)
        except Exception as e:
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            is_unathorized_error = (status_code == http_client.UNAUTHORIZED)

            if response and is_unathorized_error:
                print('Not authenticated')
            else:
                print('Unable to retrieve currently logged-in user')

            if self.app.client.debug:
                raise

            return

        print('Currently logged in as "%s".' % (user_info['username']))
        print('')
        print('Authentication method: %s' % (user_info['authentication']['method']))

        if user_info['authentication']['method'] == 'authentication token':
            print('Authentication token expire time: %s' %
                  (user_info['authentication']['token_expire']))

        print('')
        print('RBAC:')
        print(' - Enabled: %s' % (user_info['rbac']['enabled']))
        print(' - Roles: %s' % (', '.join(user_info['rbac']['roles'])))


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
        self.commands['load'] = ApiKeyLoadCommand(self.resource, self.app, self.subparsers)


class ApiKeyListCommand(resource.ResourceListCommand):
    detail_display_attributes = ['all']
    display_attributes = ['id', 'user', 'metadata']

    def __init__(self, resource, *args, **kwargs):
        super(ApiKeyListCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-u', '--user', type=str,
                                 help='Only return ApiKeys belonging to the provided user')
        self.parser.add_argument('-d', '--detail', action='store_true',
                                 help='Full list of attributes.')
        self.parser.add_argument('--show-secrets', action='store_true',
                                 help='Full list of attributes.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        filters = {}
        filters['user'] = args.user
        filters.update(**kwargs)
        # show_secrets is not a filter but a query param. There is some special
        # handling for filters in the get method which reuqires this odd hack.
        if args.show_secrets:
            params = filters.get('params', {})
            params['show_secrets'] = True
            filters['params'] = params
        return self.manager.get_all(**filters)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        attr = self.detail_display_attributes if args.detail else args.attr
        self.print_output(instances, table.MultiColumnTable,
                          attributes=attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


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
                                 help='Optional metadata to associate with the API Keys.',
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
            message = six.text_type(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)
        if args.only_key:
            print(instance.key)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json, yaml=args.yaml)


class ApiKeyLoadCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ApiKeyLoadCommand, self).__init__(
            resource, 'load', 'Load %s from a file.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('file',
                                 help=('JSON/YAML file containing the %s(s) to load.'
                                       % resource.get_display_name().lower()),
                                 default='')

        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resources = resource.load_meta_file(args.file)
        if not resources:
            print('No %s found in %s.' % (self.resource.get_display_name().lower(), args.file))
            return None
        if not isinstance(resources, list):
            resources = [resources]
        instances = []
        for res in resources:
            # pick only the meaningful properties.
            data = {
                'user': res['user'],  # required
                'key_hash': res['key_hash'],  # required
                'metadata': res.get('metadata', {}),
                'enabled': res.get('enabled', False)
            }

            if 'id' in res:
                data['id'] = res['id']

            instance = self.resource.deserialize(data)

            try:
                result = self.manager.update(instance, **kwargs)
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == http_client.NOT_FOUND:
                    instance = self.resource.deserialize(data)
                    # Key doesn't exist yet, create it instead
                    result = self.manager.create(instance, **kwargs)
                else:
                    raise e

            instances.append(result)
        return instances

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        if instances:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=ApiKeyListCommand.display_attributes,
                              widths=args.width,
                              json=args.json, yaml=args.yaml)


class ApiKeyDeleteCommand(resource.ResourceDeleteCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK


class ApiKeyEnableCommand(resource.ResourceEnableCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK


class ApiKeyDisableCommand(resource.ResourceDisableCommand):
    pk_argument_name = 'key_or_id'  # name of the attribute which stores resource PK
