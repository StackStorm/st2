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
            self.resource.get_alias().lower(), description,
            subparsers, parent_parser=parent_parser)

        # Registers subcommands for managing the resource type
        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing %s.' %
                  self.resource.get_plural_display_name().lower()))
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

    @property
    def arg_name_for_resource_id(self):
        resource_name = self.resource.get_display_name().lower()
        return '%s-id' % resource_name.replace(' ', '-')

    def print_not_found(self, name):
        print ('%s "%s" cannot be found.' %
               (self.resource.get_display_name(), name))


class ResourceListCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers, attributes=['all']):
        super(ResourceListCommand, self).__init__(
            'list',
            'Get the list of %s.' % resource.get_plural_display_name().lower(),
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
            'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            resource, manager, subparsers)
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
        args_id = getattr(args, self.arg_name_for_resource_id)
        instance = (self.manager.get_by_name(args.name)
                    if self.id_by_name else self.manager.get_by_id(args_id))
        if not instance:
            self.print_not_found(args.name if self.id_by_name else args_id)
        else:
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)


class ResourceCreateCommand(ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ResourceCreateCommand, self).__init__(
            'create',
            'Create a new %s.' % resource.get_display_name().lower(),
            resource, manager, subparsers)
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

    def __init__(self, resource, manager, subparsers):
        super(ResourceUpdateCommand, self).__init__(
            'update',
            'Updating an existing %s.' % resource.get_display_name().lower(),
            resource, manager, subparsers)
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

    def __init__(self, resource, manager, subparsers):
        super(ResourceDeleteCommand, self).__init__(
            'delete',
            'Delete an existing %s.' % resource.get_display_name().lower(),
            resource, manager, subparsers)
        self.parser.add_argument('name',
                                 help=('Name of the %s.' %
                                       resource.get_display_name().lower()))

    def run(self, args):
        instance = self.manager.get_by_name(args.name)
        if not instance:
            self.print_not_found(args.name)
        else:
            self.manager.delete(instance)
