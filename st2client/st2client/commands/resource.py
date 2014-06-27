import os
import abc
import six
import json
import logging

from st2client import commands
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ResourceBranch(commands.Branch):

    def __init__(self, resource, description, app, subparsers,
                 parent_parser=None, id_by_name=True,
                 list_attr=['id', 'name', 'description'],
                 read_only=False, commands={}):
        self.app = app
        self.resource = resource
        super(ResourceBranch, self).__init__(
            self.resource.get_alias().lower(), description,
            subparsers, parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing %s.' %
                  self.resource.get_plural_display_name().lower()))

        # Resolves if commands need to be overridden.
        if 'help' not in commands:
            commands['help'] = ResourceHelpCommand
        if 'list' not in commands:
            commands['list'] = ResourceListCommand
        if 'get' not in commands:
            commands['get'] = ResourceGetCommand
        if 'create' not in commands:
            commands['create'] = ResourceCreateCommand
        if 'update' not in commands:
            commands['update'] = ResourceUpdateCommand
        if 'delete' not in commands:
            commands['delete'] = ResourceDeleteCommand

        # Instantiate commands.
        self.commands['help'] = commands['help'](
            self.resource, self.app, self.subparsers, self.commands)
        self.commands['list'] = commands['list'](
            self.resource, self.app, self.subparsers,
            attributes=list_attr)
        self.commands['get'] = commands['get'](
            self.resource, self.app, self.subparsers,
            id_by_name=id_by_name)
        if not read_only:
            self.commands['create'] = commands['create'](
                self.resource, self.app, self.subparsers)
            self.commands['update'] = commands['update'](
                self.resource, self.app, self.subparsers)
            self.commands['delete'] = commands['delete'](
                self.resource, self.app, self.subparsers)


class ResourceCommand(commands.Command):

    def __init__(self, name, description, resource, app, subparsers,
                 parent_parser=None):
        super(ResourceCommand, self).__init__(
            name, description, subparsers, parent_parser=parent_parser)
        self.app = app
        self.resource = resource

    @property
    def manager(self):
        return self.app.client.managers[self.resource.__name__]

    @property
    def arg_name_for_resource_id(self):
        resource_name = self.resource.get_display_name().lower()
        return '%s-id' % resource_name.replace(' ', '-')

    def print_not_found(self, name):
        print ('%s "%s" cannot be found.' %
               (self.resource.get_display_name(), name))


class ResourceHelpCommand(ResourceCommand):

    def __init__(self, resource, app, subparsers, commands, parent_parser=None):
        super(ResourceHelpCommand, self).__init__(
            'help', 'Print usage for the given command.',
            resource, app, subparsers, parent_parser=parent_parser)

        # If parent parser is the top level parser, set the command argument to
        # optional so that running "prog help" will return the program's help
        # message instead of throwing the "too few arguments" error.
        nargs = '?' if self.parent_parser and self.parent_parser.prog else None
        self.parser.add_argument('command', nargs=nargs,
                                 help='Name of the command.')

        # Registers this help command in the command list so "prog help help"
        # will return the help message for this help command.
        self.commands = commands
        self.commands['help'] = self

    def run(self, args):
        if args.command:
            command = self.commands[args.command]
            command.parser.print_help()
        else:
            if self.parent_parser and self.parent_parser.prog:
                self.parent_parser.print_help()
            else:
                self.parser.print_help()
        print


class ResourceListCommand(ResourceCommand):

    def __init__(self, resource, app, subparsers, attributes=['all']):
        super(ResourceListCommand, self).__init__(
            'list',
            'Get the list of %s.' % resource.get_plural_display_name().lower(),
            resource, app, subparsers)
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

    def __init__(self, resource, app, subparsers, id_by_name=True):
        super(ResourceGetCommand, self).__init__(
            'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            resource, app, subparsers)
        self.id_by_name = id_by_name
        if self.id_by_name:
            self.parser.add_argument('name',
                                     help=('Name of the %s.' %
                                           resource.get_display_name().lower()))
        else:
            self.parser.add_argument(self.arg_name_for_resource_id,
                                     help=('Identifier for the %s.' %
                                           resource.get_display_name().lower()))
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=[],
                                 help=('List of attributes to include in the '
                                       'output. "all" or unspecified will '
                                       'return all attributes.'))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        args_id = getattr(args, self.arg_name_for_resource_id, None)
        instance = (self.manager.get_by_name(args.name)
                    if self.id_by_name else self.manager.get_by_id(args_id))
        if not instance:
            self.print_not_found(args.name if self.id_by_name else args_id)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)


class ResourceCreateCommand(ResourceCommand):

    def __init__(self, resource, app, subparsers):
        super(ResourceCreateCommand, self).__init__(
            'create',
            'Create a new %s.' % resource.get_display_name().lower(),
            resource, app, subparsers)
        self.parser.add_argument('file',
                                 help=('JSON file containing the %s to create.'
                                       % resource.get_display_name().lower()))
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

    def __init__(self, resource, app, subparsers):
        super(ResourceUpdateCommand, self).__init__(
            'update',
            'Updating an existing %s.' % resource.get_display_name().lower(),
            resource, app, subparsers)
        self.parser.add_argument(self.arg_name_for_resource_id,
                                 help=('Identifier for the %s to be updated.' %
                                       resource.get_display_name().lower()))
        self.parser.add_argument('file',
                                 help=('JSON file containing the %s to update.'
                                       % resource.get_display_name().lower()))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        with open(args.file, 'r') as f:
            data = json.loads(f.read())
            instance = self.resource.deserialize(data)
            args_id = getattr(args, self.arg_name_for_resource_id)
            if not getattr(instance, 'id', None):
                instance.id = args_id
            else:
                if instance.id != args_id:
                    raise Exception('The value for the %s id in the JSON file '
                                    'does not match the %s provided in the '
                                    'command line arguments.' %
                                    (self.resource.get_display_name().lower(),
                                     self.arg_name_for_resource_id))
            instance = self.manager.update(instance)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json)


class ResourceDeleteCommand(ResourceCommand):

    def __init__(self, resource, app, subparsers):
        super(ResourceDeleteCommand, self).__init__(
            'delete',
            'Delete an existing %s.' % resource.get_display_name().lower(),
            resource, app, subparsers)
        self.parser.add_argument('name',
                                 help=('Name of the %s.' %
                                       resource.get_display_name().lower()))

    def run(self, args):
        instance = self.manager.get_by_name(args.name)
        if not instance:
            self.print_not_found(args.name)
        else:
            self.manager.delete(instance)
