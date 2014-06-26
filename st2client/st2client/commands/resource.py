import os
import abc
import six
import json
import logging

from st2client import commands
from st2client.commands import help
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ResourceBranch(commands.Branch):

    def __init__(self, resource, manager, description, subparsers,
                 parent_parser=None, id_by_name=True,
                 list_attr=['id', 'name', 'description'],
                 read_only=False, override_help=None):
        self.resource = resource
        self.manager = manager
        super(ResourceBranch, self).__init__(
            self.resource.__name__.lower(), description,
            subparsers, parent_parser=parent_parser)

        # Registers subcommands for managing the resource type
        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing %s.' %
                  self.resource._plural.lower()))
        if not override_help:
            help.HelpCommand(self.subparsers, self.commands)
        else:
            override_help(self.subparsers, self.commands)
        self.commands['list'] = ResourceListCommand(
            self.resource, self.manager, self.subparsers,
            attributes=list_attr)
        self.commands['get'] = ResourceGetCommand(
            self.resource, self.manager, self.subparsers,
            id_by_name=id_by_name)
        if not read_only:
            self.commands['create'] = ResourceCreateCommand(
                self.resource, self.manager, self.subparsers)
            self.commands['update'] = ResourceUpdateCommand(
                self.resource, self.manager, self.subparsers)
            self.commands['delete'] = ResourceDeleteCommand(
                self.resource, self.manager, self.subparsers)


class ResourceCommand(commands.Command):

    def __init__(self, command, description, resource, manager, subparsers):
        super(ResourceCommand, self).__init__(command, description, subparsers)
        self.resource = resource
        self.manager = manager

    def print_not_found(self, name):
        print '%s "%s" cannot be found.' % (self.resource.__name__, name)


class ResourceListCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers, attributes=['all']):
        super(ResourceListCommand, self).__init__(
            'list', 'Get the list of %s.' % resource._plural.lower(),
            resource, manager, subparsers)
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=[25],
                                 help=('Set the width of columns in output.'))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        instances = self.manager.get_all()
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json)


class ResourceGetCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers, id_by_name=True):
        super(ResourceGetCommand, self).__init__(
            'get', 'Get individual %s.' % resource.__name__.lower(),
            resource, manager, subparsers)
        self.id_by_name = id_by_name
        if self.id_by_name:
            self.parser.add_argument('name',
                                     help=('Name of the %s.' %
                                           resource.__name__.lower()))
        else:
            self.parser.add_argument('id',
                                     help=('ID of the %s.' %
                                           resource.__name__.lower()))
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=[],
                                 help=('List of attributes to include in the '
                                       'output. "all" or unspecified will '
                                       'return all attributes.'))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        instance = (self.manager.get_by_name(args.name)
                    if self.id_by_name else self.manager.get_by_id(args.id))
        if not instance:
            self.print_not_found(args.name if self.id_by_name else args.id)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)


class ResourceCreateCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ResourceCreateCommand, self).__init__(
            'create', 'Create a new %s.' % resource.__name__.lower(),
            resource, manager, subparsers)
        self.parser.add_argument('file',
                                 help='JSON file containing the '
                                      'rule(s) to create.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        with open(args.file, 'r') as f:
            data = json.loads(f.read())
            instance = self.resource.deserialize(data)
            instance = self.manager.create(instance)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json)


class ResourceUpdateCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ResourceUpdateCommand, self).__init__(
            'update', 'Updating an existing %s.' % resource.__name__.lower(),
            resource, manager, subparsers)
        self.parser.add_argument('id',
                                 help=('ID of the %s to be updated.' %
                                       resource.__name__.lower()))
        self.parser.add_argument('file',
                                 help='JSON file containing the '
                                      'rule(s) to create.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        with open(args.file, 'r') as f:
            data = json.loads(f.read())
            instance = self.resource.deserialize(data)
            if not getattr(instance, 'id', None):
                instance.id = args.id
            else:
                if instance.id != args.id:
                    raise Exception('ID of the %s in the JSON file does not '
                                    'match the ID provided in the argument.' %
                                    self.resource.__name__.lower())
            instance = self.manager.update(instance)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json)


class ResourceDeleteCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ResourceDeleteCommand, self).__init__(
            'delete', 'Delete an existing %s.' % resource.__name__.lower(),
            resource, manager, subparsers)
        self.parser.add_argument('name',
                                 help=('Name of the %s.' %
                                       resource.__name__.lower()))

    def run(self, args):
        instance = self.manager.get_by_name(args.name)
        if not instance:
            self.print_not_found(args.name)
        else:
            self.manager.delete(instance)
