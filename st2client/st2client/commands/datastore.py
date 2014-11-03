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

import os
import json
import logging
from os.path import join as pjoin

from st2client.models import datastore
from st2client.commands import resource
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.formatters import table
import six


LOG = logging.getLogger(__name__)


class KeyValuePairBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(KeyValuePairBranch, self).__init__(
            datastore.KeyValuePair, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': KeyValuePairListCommand,
                'get': KeyValuePairGetCommand,
                'create': KeyValuePairCreateCommand,
                'update': KeyValuePairUpdateCommand
            })

        # Registers extended commands
        self.commands['load'] = KeyValuePairLoadCommand(
            self.resource, self.app, self.subparsers)


class KeyValuePairListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'name', 'value']


class KeyValuePairGetCommand(resource.ResourceGetCommand):
    display_attributes = ['id', 'name', 'value']


class KeyValuePairCreateCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(KeyValuePairCreateCommand, self).__init__(resource, 'create',
            'Create a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name', help='Key name.')
        self.parser.add_argument('value', help='Value paired with the key.')

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        instance = self.resource(name=args.name, value=args.value)
        return self.manager.create(instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['id', 'name', 'value'], json=args.json)


class KeyValuePairUpdateCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(KeyValuePairUpdateCommand, self).__init__(resource, 'update',
            'Update an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name_or_id',
                                 metavar='name-or-id',
                                 help='Name or ID of the key value pair.')
        self.parser.add_argument('value', help='Value paired with the key.')

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        instance = self.get_resource(args.name_or_id, **kwargs)
        instance.value = args.value
        return self.manager.update(instance, **kwargs)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['id', 'name', 'value'], json=args.json)


class KeyValuePairLoadCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        help_text = ('Load a list of %s from file.' %
                     resource.get_plural_display_name().lower())
        super(KeyValuePairLoadCommand, self).__init__(resource, 'load',
            help_text, *args, **kwargs)

        self.parser.add_argument(
            'file', help=('JSON file containing the %s to create.'
                          % resource.get_plural_display_name().lower()))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        file_path = os.path.normpath(pjoin(os.getcwd(), args.file))

        if not os.path.exists(args.file):
            raise ValueError('File "%s" doesn\'t exist' % (file_path))

        if not os.path.isfile(args.file):
            raise ValueError('"%s" is not a file' % (file_path))

        with open(file_path, 'r') as f:
            instances = []
            kvps = json.loads(f.read())
            for k, v in six.iteritems(kvps):
                try:
                    instance = self.get_resource(k, **kwargs)
                except resource.ResourceNotFoundError:
                    instance = None
                if not instance:
                    instance = self.resource(name=k, value=v)
                    instances.append(self.manager.create(instance, **kwargs))
                else:
                    instance.value = v
                    instances.append(self.manager.update(instance, **kwargs))
            return instances

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=['id', 'name', 'value'], json=args.json)
