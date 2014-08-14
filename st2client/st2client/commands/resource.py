import os
import abc
import six
import json
import logging

from st2client import commands
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ResourceCommandError(Exception):
    pass


class ResourceNotFoundError(Exception):
    pass


class ResourceBranch(commands.Branch):

    def __init__(self, resource, description, app, subparsers,
                 parent_parser=None, read_only=False, commands={}):

        self.resource = resource
        super(ResourceBranch, self).__init__(
            self.resource.get_alias().lower(), description,
            app, subparsers, parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help=('List of commands for managing %s.' %
                  self.resource.get_plural_display_name().lower()))

        # Resolves if commands need to be overridden.
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
        args = [self.resource, self.app, self.subparsers]
        self.commands['list'] = commands['list'](*args)
        self.commands['get'] = commands['get'](*args)
        if not read_only:
            self.commands['create'] = commands['create'](*args)
            self.commands['update'] = commands['update'](*args)
            self.commands['delete'] = commands['delete'](*args)


class ResourceCommand(commands.Command):

    def __init__(self, resource, *args, **kwargs):
        super(ResourceCommand, self).__init__(*args, **kwargs)
        self.resource = resource

    @property
    def manager(self):
        return self.app.client.managers[self.resource.__name__]

    @property
    def arg_name_for_resource_id(self):
        resource_name = self.resource.get_display_name().lower()
        return '%s-id' % resource_name.replace(' ', '-')

    def print_not_found(self, name):
        print ('%s "%s" is not found.\n' %
               (self.resource.get_display_name(), name))

    def get_resource(self, name_or_id):
        instance = self.manager.get_by_name(name_or_id)
        if not instance:
            try:
                instance = self.manager.get_by_id(name_or_id)
            except:
                pass
        if not instance:
            raise ResourceNotFoundError()
        return instance

class ResourceListCommand(ResourceCommand):

    display_attributes = ['id', 'name', 'description']

    def __init__(self, resource, *args, **kwargs):
        super(ResourceListCommand, self).__init__(resource, 'list',
            'Get the list of %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=[28],
                                 help=('Set the width of columns in output.'))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args, **kwargs):
        return self.manager.get_all()

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json)


class ResourceGetCommand(ResourceCommand):

    display_attributes = ['all']

    def __init__(self, resource, *args, **kwargs):
        super(ResourceGetCommand, self).__init__(resource, 'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name_or_id',
                                 metavar='name-or-id',
                                 help=('Name or ID of the %s.' %
                                       resource.get_display_name().lower()))
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" or unspecified will '
                                       'return all attributes.'))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args, **kwargs):
        return self.get_resource(args.name_or_id)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)
        except ResourceNotFoundError as e:
            self.print_not_found(args.name_or_id)


class ResourceCreateCommand(ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ResourceCreateCommand, self).__init__(resource, 'create',
            'Create a new %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('file',
                                 help=('JSON file containing the %s to create.'
                                       % resource.get_display_name().lower()))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args, **kwargs):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        with open(args.file, 'r') as f:
            data = json.loads(f.read())
            instance = self.resource.deserialize(data)
            return self.manager.create(instance)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)


class ResourceUpdateCommand(ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ResourceUpdateCommand, self).__init__(resource, 'update',
            'Updating an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name_or_id',
                                 metavar='name-or-id',
                                 help=('Name or ID of the %s to be updated.' %
                                       resource.get_display_name().lower()))
        self.parser.add_argument('file',
                                 help=('JSON file containing the %s to update.'
                                       % resource.get_display_name().lower()))
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args, **kwargs):
        if not os.path.isfile(args.file):
            raise Exception('File "%s" does not exist.' % args.file)
        instance = self.get_resource(args.name_or_id)
        with open(args.file, 'r') as f:
            data = json.loads(f.read())
            modified_instance = self.resource.deserialize(data)
            if not getattr(modified_instance, 'id', None):
                modified_instance.id = instance.id
            else:
                if modified_instance.id != instance.id:
                    raise Exception('The value for the %s id in the JSON file '
                                    'does not match the ID provided in the '
                                    'command line arguments.' %
                                    self.resource.get_display_name().lower())
            return self.manager.update(modified_instance)

    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)


class ResourceDeleteCommand(ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ResourceDeleteCommand, self).__init__(resource, 'delete',
            'Delete an existing %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('name_or_id',
                                 metavar='name-or-id',
                                 help=('Name or ID of the %s.' %
                                       resource.get_display_name().lower()))

    def run(self, args, **kwargs):
        instance = self.get_resource(args.name_or_id)
        self.manager.delete(instance)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
        except ResourceNotFoundError as e:
            self.print_not_found(args.name)
