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

import os
import abc
import six
import json
import logging
import traceback

from functools import wraps

import yaml
from six.moves import http_client

from st2client import commands
from st2client.exceptions.operations import OperationFailureException
from st2client.formatters import table

ALLOWED_EXTS = ['.json', '.yaml', '.yml']
PARSER_FUNCS = {'.json': json.load, '.yml': yaml.safe_load, '.yaml': yaml.safe_load}
LOG = logging.getLogger(__name__)


def add_auth_token_to_kwargs_from_cli(func):
    @wraps(func)
    def decorate(*args, **kwargs):
        ns = args[1]
        if getattr(ns, 'token', None):
            kwargs['token'] = ns.token
        if getattr(ns, 'api_key', None):
            kwargs['api_key'] = ns.api_key
        return func(*args, **kwargs)
    return decorate


class ResourceCommandError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


class ResourceBranch(commands.Branch):

    def __init__(self, resource, description, app, subparsers,
                 parent_parser=None, read_only=False, commands=None,
                 has_disable=False):

        self.resource = resource
        super(ResourceBranch, self).__init__(
            self.resource.get_alias().lower(), description,
            app, subparsers, parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing %s.' %
                  self.resource.get_plural_display_name().lower()))

        # Resolves if commands need to be overridden.
        commands = commands or {}
        cmd_map = {
            "list": ResourceListCommand,
            "get": ResourceGetCommand,
            "create": ResourceCreateCommand,
            "update": ResourceUpdateCommand,
            "delete": ResourceDeleteCommand,
            "enable": ResourceEnableCommand,
            "disable": ResourceDisableCommand
        }
        for cmd, cmd_class in cmd_map.items():
            if cmd not in commands:
                commands[cmd] = cmd_class

        # Instantiate commands.
        args = [self.resource, self.app, self.subparsers]
        self.commands['list'] = commands['list'](*args)
        self.commands['get'] = commands['get'](*args)

        if not read_only:
            self.commands['create'] = commands['create'](*args)
            self.commands['update'] = commands['update'](*args)
            self.commands['delete'] = commands['delete'](*args)

        if has_disable:
            self.commands['enable'] = commands['enable'](*args)
            self.commands['disable'] = commands['disable'](*args)


@six.add_metaclass(abc.ABCMeta)
class ResourceCommand(commands.Command):
    pk_argument_name = None

    def __init__(self, resource, *args, **kwargs):

        has_token_opt = kwargs.pop('has_token_opt', True)

        super(ResourceCommand, self).__init__(*args, **kwargs)

        self.resource = resource

        if has_token_opt:
            self.parser.add_argument('-t', '--token', dest='token',
                                     help='Access token for user authentication. '
                                          'Get ST2_AUTH_TOKEN from the environment '
                                          'variables by default.')
            self.parser.add_argument('--api-key', dest='api_key',
                                     help='Api Key for user authentication. '
                                          'Get ST2_API_KEY from the environment '
                                          'variables by default.')

        # Formatter flags
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Print output in JSON format.')
        self.parser.add_argument('-y', '--yaml',
                                 action='store_true', dest='yaml',
                                 help='Print output in YAML format.')

    @property
    def manager(self):
        return self.app.client.managers[self.resource.__name__]

    @property
    def arg_name_for_resource_id(self):
        resource_name = self.resource.get_display_name().lower()
        return '%s-id' % resource_name.replace(' ', '-')

    def print_not_found(self, name):
        print('%s "%s" is not found.\n' %
              (self.resource.get_display_name(), name))

    def get_resource(self, name_or_id, **kwargs):
        pk_argument_name = self.pk_argument_name

        if pk_argument_name == 'name_or_id':
            instance = self.get_resource_by_name_or_id(name_or_id=name_or_id, **kwargs)
        elif pk_argument_name == 'ref_or_id':
            instance = self.get_resource_by_ref_or_id(ref_or_id=name_or_id, **kwargs)
        else:
            instance = self.get_resource_by_pk(pk=name_or_id, **kwargs)

        return instance

    def get_resource_by_pk(self, pk, **kwargs):
        """
        Retrieve resource by a primary key.
        """
        try:
            instance = self.manager.get_by_id(pk, **kwargs)
        except Exception as e:
            traceback.print_exc()
            # Hack for "Unauthorized" exceptions, we do want to propagate those
            response = getattr(e, 'response', None)
            status_code = getattr(response, 'status_code', None)
            if status_code and status_code == http_client.UNAUTHORIZED:
                raise e

            instance = None

        return instance

    def get_resource_by_id(self, id, **kwargs):
        instance = self.get_resource_by_pk(pk=id, **kwargs)

        if not instance:
            message = ('Resource with id "%s" doesn\'t exist.' % (id))
            raise ResourceNotFoundError(message)
        return instance

    def get_resource_by_name(self, name, **kwargs):
        """
        Retrieve resource by name.
        """
        instance = self.manager.get_by_name(name, **kwargs)
        return instance

    def get_resource_by_name_or_id(self, name_or_id, **kwargs):
        instance = self.get_resource_by_name(name=name_or_id, **kwargs)
        if not instance:
            instance = self.get_resource_by_pk(pk=name_or_id, **kwargs)

        if not instance:
            message = ('Resource with id or name "%s" doesn\'t exist.' %
                       (name_or_id))
            raise ResourceNotFoundError(message)
        return instance

    def get_resource_by_ref_or_id(self, ref_or_id, **kwargs):
        instance = self.manager.get_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)

        if not instance:
            message = ('Resource with id or reference "%s" doesn\'t exist.' %
                       (ref_or_id))
            raise ResourceNotFoundError(message)
        return instance

    @abc.abstractmethod
    def run(self, args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def run_and_print(self, args, **kwargs):
        raise NotImplementedError

    def _get_metavar_for_argument(self, argument):
        return argument.replace('_', '-')

    def _get_help_for_argument(self, resource, argument):
        argument_display_name = argument.title()
        resource_display_name = resource.get_display_name().lower()

        if 'ref' in argument:
            result = ('Reference or ID of the %s.' % (resource_display_name))
        elif 'name_or_id' in argument:
            result = ('Name or ID of the %s.' % (resource_display_name))
        else:
            result = ('%s of the %s.' % (argument_display_name, resource_display_name))

        return result


class ResourceTableCommand(ResourceCommand):
    display_attributes = ['id', 'name', 'description']

    def __init__(self, resource, name, description, *args, **kwargs):
        super(ResourceTableCommand, self).__init__(resource, name, description,
                                                   *args, **kwargs)

        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.get_all(**kwargs)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json, yaml=args.yaml)


class ResourceListCommand(ResourceTableCommand):
    def __init__(self, resource, *args, **kwargs):
        super(ResourceListCommand, self).__init__(
            resource, 'list', 'Get the list of %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)


class ContentPackResourceListCommand(ResourceListCommand):
    """
    Base command class for use with resources which belong to a content pack.
    """
    def __init__(self, resource, *args, **kwargs):
        super(ContentPackResourceListCommand, self).__init__(resource,
                                                             *args, **kwargs)

        self.parser.add_argument('-p', '--pack', type=str,
                                 help=('Only return resources belonging to the'
                                       ' provided pack'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        filters = {'pack': args.pack}
        filters.update(**kwargs)
        return self.manager.get_all(**filters)


class ResourceGetCommand(ResourceCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'name', 'description']

    pk_argument_name = 'name_or_id'  # name of the attribute which stores resource PK

    help_string = None

    def __init__(self, resource, *args, **kwargs):
        super(ResourceGetCommand, self).__init__(
            resource, 'get',
            self.help_string or 'Get individual %s.' % resource.get_display_name().lower(),
            *args, **kwargs
        )

        argument = self.pk_argument_name
        metavar = self._get_metavar_for_argument(argument=self.pk_argument_name)
        help = self._get_help_for_argument(resource=resource,
                                           argument=self.pk_argument_name)

        self.parser.add_argument(argument,
                                 metavar=metavar,
                                 help=help)
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" or unspecified will '
                                       'return all attributes.'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        return self.get_resource_by_id(resource_id, **kwargs)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json, yaml=args.yaml,
                              attribute_display_order=self.attribute_display_order)
        except ResourceNotFoundError:
            resource_id = getattr(args, self.pk_argument_name, None)
            self.print_not_found(resource_id)
            raise OperationFailureException('Resource %s not found.' % resource_id)


class ContentPackResourceGetCommand(ResourceGetCommand):
    """
    Command for retrieving a single resource which belongs to a content pack.

    Note: All the resources which belong to the content pack can either be
    retrieved by a reference or by an id.
    """

    attribute_display_order = ['id', 'pack', 'name', 'description']

    pk_argument_name = 'ref_or_id'

    def get_resource(self, ref_or_id, **kwargs):
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)


class ResourceCreateCommand(ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ResourceCreateCommand, self).__init__(resource, 'create',
            'Create a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('file',
                                 help=('JSON/YAML file containing the %s to create.'
                                       % resource.get_display_name().lower()))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        data = load_meta_file(args.file)
        instance = self.resource.deserialize(data)
        return self.manager.create(instance, **kwargs)

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


class ResourceUpdateCommand(ResourceCommand):
    pk_argument_name = 'name_or_id'

    def __init__(self, resource, *args, **kwargs):
        super(ResourceUpdateCommand, self).__init__(resource, 'update',
            'Updating an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        argument = self.pk_argument_name
        metavar = self._get_metavar_for_argument(argument=self.pk_argument_name)
        help = self._get_help_for_argument(resource=resource,
                                           argument=self.pk_argument_name)

        self.parser.add_argument(argument,
                                 metavar=metavar,
                                 help=help)
        self.parser.add_argument('file',
                                 help=('JSON/YAML file containing the %s to update.'
                                       % resource.get_display_name().lower()))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        instance = self.get_resource(resource_id, **kwargs)
        data = load_meta_file(args.file)
        modified_instance = self.resource.deserialize(data)

        if not getattr(modified_instance, 'id', None):
            modified_instance.id = instance.id
        else:
            if modified_instance.id != instance.id:
                raise Exception('The value for the %s id in the JSON/YAML file '
                                'does not match the ID provided in the '
                                'command line arguments.' %
                                self.resource.get_display_name().lower())
        return self.manager.update(modified_instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        try:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json, yaml=args.yaml)
        except Exception as e:
            print('ERROR: %s' % e.message)
            raise OperationFailureException(e.message)


class ContentPackResourceUpdateCommand(ResourceUpdateCommand):
    pk_argument_name = 'ref_or_id'


class ResourceEnableCommand(ResourceCommand):
    pk_argument_name = 'name_or_id'

    def __init__(self, resource, *args, **kwargs):
        super(ResourceEnableCommand, self).__init__(resource, 'enable',
            'Enable an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        argument = self.pk_argument_name
        metavar = self._get_metavar_for_argument(argument=self.pk_argument_name)
        help = self._get_help_for_argument(resource=resource,
                                           argument=self.pk_argument_name)

        self.parser.add_argument(argument,
                                 metavar=metavar,
                                 help=help)

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        instance = self.get_resource(resource_id, **kwargs)

        data = instance.serialize()

        if 'ref' in data:
            del data['ref']

        data['enabled'] = True
        modified_instance = self.resource.deserialize(data)

        return self.manager.update(modified_instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json, yaml=args.yaml)


class ContentPackResourceEnableCommand(ResourceEnableCommand):
    pk_argument_name = 'ref_or_id'


class ResourceDisableCommand(ResourceCommand):
    pk_argument_name = 'name_or_id'

    def __init__(self, resource, *args, **kwargs):
        super(ResourceDisableCommand, self).__init__(resource, 'disable',
            'Disable an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        argument = self.pk_argument_name
        metavar = self._get_metavar_for_argument(argument=self.pk_argument_name)
        help = self._get_help_for_argument(resource=resource,
                                           argument=self.pk_argument_name)

        self.parser.add_argument(argument,
                                 metavar=metavar,
                                 help=help)

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        instance = self.get_resource(resource_id, **kwargs)

        data = instance.serialize()

        if 'ref' in data:
            del data['ref']

        data['enabled'] = False
        modified_instance = self.resource.deserialize(data)

        return self.manager.update(modified_instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json, yaml=args.yaml)


class ContentPackResourceDisableCommand(ResourceDisableCommand):
    pk_argument_name = 'ref_or_id'


class ResourceDeleteCommand(ResourceCommand):
    pk_argument_name = 'name_or_id'

    def __init__(self, resource, *args, **kwargs):
        super(ResourceDeleteCommand, self).__init__(resource, 'delete',
            'Delete an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        argument = self.pk_argument_name
        metavar = self._get_metavar_for_argument(argument=self.pk_argument_name)
        help = self._get_help_for_argument(resource=resource,
                                           argument=self.pk_argument_name)

        self.parser.add_argument(argument,
                                 metavar=metavar,
                                 help=help)

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        instance = self.get_resource(resource_id, **kwargs)
        self.manager.delete(instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)

        try:
            self.run(args, **kwargs)
            print('Resource with id "%s" has been successfully deleted.' % (resource_id))
        except ResourceNotFoundError:
            self.print_not_found(resource_id)
            raise OperationFailureException('Resource %s not found.' % resource_id)


class ContentPackResourceDeleteCommand(ResourceDeleteCommand):
    """
    Base command class for deleting a resource which belongs to a content pack.
    """

    pk_argument_name = 'ref_or_id'


def load_meta_file(file_path):
    if not os.path.isfile(file_path):
        raise Exception('File "%s" does not exist.' % file_path)

    file_name, file_ext = os.path.splitext(file_path)
    if file_ext not in ALLOWED_EXTS:
        raise Exception('Unsupported meta type %s, file %s. Allowed: %s' %
                        (file_ext, file_path, ALLOWED_EXTS))

    with open(file_path, 'r') as f:
        return PARSER_FUNCS[file_ext](f)
