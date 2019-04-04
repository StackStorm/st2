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
import json
import logging

from os.path import join as pjoin

import six

from st2client.commands import resource
from st2client.commands.noop import NoopCommand
from st2client.formatters import table
from st2client.models.keyvalue import KeyValuePair
from st2client.utils.date import format_isodate_for_user_timezone

LOG = logging.getLogger(__name__)

DEFAULT_LIST_SCOPE = 'all'
DEFAULT_GET_SCOPE = 'system'
DEFAULT_CUD_SCOPE = 'system'


class KeyValuePairBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(KeyValuePairBranch, self).__init__(
            KeyValuePair, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': KeyValuePairListCommand,
                'get': KeyValuePairGetCommand,
                'delete': KeyValuePairDeleteCommand,
                'create': NoopCommand,
                'update': NoopCommand
            })

        # Registers extended commands
        self.commands['set'] = KeyValuePairSetCommand(self.resource, self.app,
                                                      self.subparsers)
        self.commands['load'] = KeyValuePairLoadCommand(
            self.resource, self.app, self.subparsers)
        self.commands['delete_by_prefix'] = KeyValuePairDeleteByPrefixCommand(
            self.resource, self.app, self.subparsers)

        # Remove unsupported commands
        # TODO: Refactor parent class and make it nicer
        del self.commands['create']
        del self.commands['update']


class KeyValuePairListCommand(resource.ResourceTableCommand):
    display_attributes = ['name', 'value', 'secret', 'encrypted', 'scope', 'user',
                          'expire_timestamp']
    attribute_transform_functions = {
        'expire_timestamp': format_isodate_for_user_timezone,
    }

    def __init__(self, resource, *args, **kwargs):

        self.default_limit = 50

        super(KeyValuePairListCommand, self).__init__(resource, 'list',
                                                      'Get the list of the %s most recent %s.' %
                                                      (self.default_limit,
                                                       resource.get_plural_display_name().lower()),
                                                      *args, **kwargs)
        self.resource_name = resource.get_plural_display_name().lower()
        # Filter options
        self.parser.add_argument('--prefix', help=('Only return values with names starting with '
                                                   'the provided prefix.'))
        self.parser.add_argument('-d', '--decrypt', action='store_true',
                                 help='Decrypt secrets and displays plain text.')
        self.parser.add_argument('-s', '--scope', default=DEFAULT_LIST_SCOPE, dest='scope',
                                 help='Scope item is under. Example: "user".')
        self.parser.add_argument('-u', '--user', dest='user', default=None,
                                 help='User for user scoped items (admin only).')
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=self.default_limit,
                                 help=('List N most recent %s. Use -n -1 to fetch the full result \
                                       set.' % self.resource_name))

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.prefix:
            kwargs['prefix'] = args.prefix

        decrypt = getattr(args, 'decrypt', False)
        kwargs['params'] = {'decrypt': str(decrypt).lower()}
        scope = getattr(args, 'scope', DEFAULT_LIST_SCOPE)
        kwargs['params']['scope'] = scope
        if args.user:
            kwargs['params']['user'] = args.user
        kwargs['params']['limit'] = args.last

        return self.manager.query_with_count(**kwargs)

    @resource.add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        instances, count = self.run(args, **kwargs)
        if args.json or args.yaml:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml,
                              attribute_transform_functions=self.attribute_transform_functions)
        else:
            self.print_output(instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              attribute_transform_functions=self.attribute_transform_functions)

            if args.last and count and count > args.last:
                table.SingleRowTable.note_box(self.resource_name, args.last)


class KeyValuePairGetCommand(resource.ResourceGetCommand):
    pk_argument_name = 'name'
    display_attributes = ['name', 'value', 'secret', 'encrypted', 'scope', 'expire_timestamp']

    def __init__(self, kv_resource, *args, **kwargs):
        super(KeyValuePairGetCommand, self).__init__(kv_resource, *args, **kwargs)
        self.parser.add_argument('-d', '--decrypt', action='store_true',
                                 help='Decrypt secret if encrypted and show plain text.')
        self.parser.add_argument('-s', '--scope', default=DEFAULT_GET_SCOPE, dest='scope',
                                 help='Scope item is under. Example: "user".')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_name = getattr(args, self.pk_argument_name, None)
        decrypt = getattr(args, 'decrypt', False)
        scope = getattr(args, 'scope', DEFAULT_GET_SCOPE)
        kwargs['params'] = {'decrypt': str(decrypt).lower()}
        kwargs['params']['scope'] = scope
        return self.get_resource_by_id(id=resource_name, **kwargs)


class KeyValuePairSetCommand(resource.ResourceCommand):
    display_attributes = ['name', 'value', 'scope', 'expire_timestamp']

    def __init__(self, resource, *args, **kwargs):
        super(KeyValuePairSetCommand, self).__init__(
            resource, 'set',
            'Set an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs
        )

        # --encrypt and --encrypted options are mutually exclusive.
        # --encrypt implies provided value is plain text and should be encrypted whereas
        # --encrypted implies value is already encrypted and should be treated as-is.
        encryption_group = self.parser.add_mutually_exclusive_group()
        encryption_group.add_argument('-e', '--encrypt', dest='secret',
                                      action='store_true',
                                      help='Encrypt value before saving.')
        encryption_group.add_argument('--encrypted', dest='encrypted',
                                      action='store_true',
                                      help=('Value provided is already encrypted with the '
                                            'instance crypto key and should be stored as-is.'))

        self.parser.add_argument('name',
                                 metavar='name',
                                 help='Name of the key value pair.')
        self.parser.add_argument('value', help='Value paired with the key.')
        self.parser.add_argument('-l', '--ttl', dest='ttl', type=int, default=None,
                                 help='TTL (in seconds) for this value.')
        self.parser.add_argument('-s', '--scope', dest='scope', default=DEFAULT_CUD_SCOPE,
                                 help='Specify the scope under which you want ' +
                                      'to place the item.')
        self.parser.add_argument('-u', '--user', dest='user', default=None,
                                 help='User for user scoped items (admin only).')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        instance = KeyValuePair()
        instance.id = args.name  # TODO: refactor and get rid of id
        instance.name = args.name
        instance.value = args.value
        instance.scope = args.scope
        instance.user = args.user

        if args.secret:
            instance.secret = args.secret

        if args.encrypted:
            instance.encrypted = args.encrypted

        if args.ttl:
            instance.ttl = args.ttl

        return self.manager.update(instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=self.display_attributes, json=args.json,
                          yaml=args.yaml)


class KeyValuePairDeleteCommand(resource.ResourceDeleteCommand):
    pk_argument_name = 'name'

    def __init__(self, resource, *args, **kwargs):
        super(KeyValuePairDeleteCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-s', '--scope', dest='scope', default=DEFAULT_CUD_SCOPE,
                                 help='Specify the scope under which you want ' +
                                      'to place the item.')
        self.parser.add_argument('-u', '--user', dest='user', default=None,
                                 help='User for user scoped items (admin only).')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        scope = getattr(args, 'scope', DEFAULT_CUD_SCOPE)
        kwargs['params'] = {}
        kwargs['params']['scope'] = scope
        kwargs['params']['user'] = args.user
        instance = self.get_resource(resource_id, **kwargs)

        if not instance:
            raise resource.ResourceNotFoundError('KeyValuePair with id "%s" not found'
                                                 % resource_id)

        instance.id = resource_id  # TODO: refactor and get rid of id
        self.manager.delete(instance, **kwargs)


class KeyValuePairDeleteByPrefixCommand(resource.ResourceCommand):
    """
    Commands which delete all the key value pairs which match the provided
    prefix.
    """
    def __init__(self, resource, *args, **kwargs):
        super(KeyValuePairDeleteByPrefixCommand, self).__init__(resource, 'delete_by_prefix',
                                                                'Delete KeyValue pairs which \
                                                                 match the provided prefix',
                                                                *args, **kwargs)

        self.parser.add_argument('-p', '--prefix', required=True,
                                 help='Name prefix (e.g. twitter.TwitterSensor:)')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        prefix = args.prefix
        key_pairs = self.manager.get_all(prefix=prefix)

        to_delete = []
        for key_pair in key_pairs:
            key_pair.id = key_pair.name
            to_delete.append(key_pair)

        deleted = []
        for key_pair in to_delete:
            self.manager.delete(instance=key_pair, **kwargs)
            deleted.append(key_pair)

        return deleted

    def run_and_print(self, args, **kwargs):
        # TODO: Need to use args, instead of kwargs (args=) because of bad API
        # FIX ME
        deleted = self.run(args, **kwargs)
        key_ids = [key_pair.id for key_pair in deleted]

        print('Deleted %s keys' % (len(deleted)))
        print('Deleted key ids: %s' % (', '.join(key_ids)))


class KeyValuePairLoadCommand(resource.ResourceCommand):
    pk_argument_name = 'name'
    display_attributes = ['name', 'value']

    def __init__(self, resource, *args, **kwargs):
        help_text = ('Load a list of %s from file.' %
                     resource.get_plural_display_name().lower())
        super(KeyValuePairLoadCommand, self).__init__(resource, 'load',
                                                      help_text, *args, **kwargs)

        self.parser.add_argument('-c', '--convert', action='store_true',
                                 help=('Convert non-string types (hash, array, boolean,'
                                       ' int, float) to a JSON string before loading it'
                                       ' into the datastore.'))
        self.parser.add_argument(
            'file', help=('JSON/YAML file containing the %s(s) to load'
                          % resource.get_plural_display_name().lower()))

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # normalize the file path to allow for relative files to be specified
        file_path = os.path.normpath(pjoin(os.getcwd(), args.file))

        # load the data (JSON/YAML) from the file
        kvps = resource.load_meta_file(file_path)

        instances = []
        # bail out if file was empty
        if not kvps:
            return instances

        # if the data is not a list (ie. it's a single entry)
        # then make it a list so our process loop is generic
        if not isinstance(kvps, list):
            kvps = [kvps]

        for item in kvps:
            # parse required KeyValuePair properties
            name = item['name']
            value = item['value']

            # parse optional KeyValuePair properties
            scope = item.get('scope', DEFAULT_CUD_SCOPE)
            user = item.get('user', None)
            encrypted = item.get('encrypted', False)
            secret = item.get('secret', False)
            ttl = item.get('ttl', None)

            # if the value is not a string, convert it to JSON
            # all keys in the datastore must strings
            if not isinstance(value, six.string_types):
                if args.convert:
                    value = json.dumps(value)
                else:
                    raise ValueError(("Item '%s' has a value that is not a string."
                                      " Either pass in the -c/--convert option to convert"
                                      " non-string types to JSON strings automatically, or"
                                      " convert the data to a string in the file") % name)

            # create the KeyValuePair instance
            instance = KeyValuePair()
            instance.id = name  # TODO: refactor and get rid of id
            instance.name = name
            instance.value = value
            instance.scope = scope

            if user:
                instance.user = user
            if encrypted:
                instance.encrypted = encrypted
            if secret:
                instance.secret = secret
            if ttl:
                instance.ttl = ttl

            # encrypted=True and secret=True implies that the value is already encrypted and should
            # be used as such
            if encrypted and secret:
                instance.encrypted = True

            # call the API to create/update the KeyValuePair
            self.manager.update(instance, **kwargs)
            instances.append(instance)

        return instances

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=['name', 'value', 'secret', 'scope', 'user', 'ttl'],
                          json=args.json,
                          yaml=args.yaml)
