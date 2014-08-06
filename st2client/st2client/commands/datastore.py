import os
import json
import logging

from st2client import models
from st2client.models import datastore
from st2client.commands import resource
from st2client.formatters import table


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
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        instance = self.resource(name=args.name, value=args.value)
        return self.manager.create(instance)

    def run_and_print(self, args):
        instance = self.run(args)
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
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        instance = self.get_resource(args.name_or_id)
        instance.value = args.value
        return self.manager.update(instance)

    def run_and_print(self, args):
        instance = self.run(args)
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
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        with open(args.file, 'r') as f:
            instances = []
            kvps = json.loads(f.read())
            for k, v in kvps.iteritems():
                try:
                    instance = self.get_resource(k)
                except resource.ResourceNotFoundError as e:
                    instance = None
                if not instance:
                    instance = self.resource(name=k, value=v)
                    instances.append(self.manager.create(instance))
                else:
                    instance.value = v
                    instances.append(self.manager.update(instance))
            return instances

    def run_and_print(self, args):
        instances = self.run(args)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=['id', 'name', 'value'], json=args.json)
