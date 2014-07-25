import logging

from st2client import models
from st2client.models import action
from st2client.commands import resource
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            action.Action, description, app, subparsers,
            parent_parser=parent_parser)

        # Registers extended commands
        self.commands['execute'] = ActionExecuteCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class ActionExecuteCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):

        super(ActionExecuteCommand, self).__init__(resource,
            kwargs.pop('name', 'execute'),
            'Execute an action manually.',
            *args, **kwargs)

        self.parser.add_argument('name', nargs='?',
                                 help='Name of the action.')
        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')
        self.parser.add_argument('-p', '--params', nargs='+',
                                 help='List of parameters (i.e. k1=v1 k2=v2) '
                                      'to pass into the action.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        if not args.name:
            self.parser.error('too few arguments')
        action_exec_mgr = self.app.client.managers['ActionExecution']
        if not self.manager.get_by_name(args.name):
            raise Exception('Action "%s" cannot be found.' % args.name)
        instance = action.ActionExecution()
        instance.action = { "name": args.name }
        instance.parameters = {}
        if args.params:
            for kvp in args.params:
                k, v = kvp.split('=')
                instance.parameters[k] = v
        return action_exec_mgr.create(instance)

    def run_and_print(self, args):
        # Print appropriate help message if the help option is given.
        if args.help:
            if args.name:
                try:
                    action = self.manager.get_by_name(args.name)
                    print action.description
                except Exception as e:
                    print 'Action "%s" is not found.' % args.name
            else:
                self.parser.print_help()
            return

        # Execute the action.
        instance = self.run(args)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            action.ActionExecution, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={'list': ActionExecutionListCommand,
                      'get': resource.ResourceGetByIdCommand})

        # Registers extended commands
        self.commands['cancel'] = ActionExecutionCancelCommand(
            self.resource, self.app, self.subparsers)


class ActionExecutionListCommand(resource.ResourceCommand):

    display_attributes = ['id', 'action.name', 'status', 'start_timestamp']

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionListCommand, self).__init__(resource, 'list',
            'Get the list of the 50 most recent %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('--action-name',
                                 help='Action name to filter the list.')
        self.group.add_argument('--action-id',
                                 help='Action id to filter the list.')
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=50,
                                 help=('List N most recent %s; '
                                       'list all if 0.' %
                                       resource.get_plural_display_name().\
                                          lower()))
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

    def run(self, args):
        filters = dict()
        if args.action_name:
            filters['action_name'] = args.action_name
        elif args.action_id:
            filters['action_id'] = args.action_id
        return (self.manager.query(limit=args.last, **filters)
                if filters else self.manager.get_all(limit=args.last))

    def run_and_print(self, args):
        instances = self.run(args)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json)


class ActionExecutionCancelCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionCancelCommand, self).__init__(resource, 'cancel',
            'Cancels an %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('execution-id',
                                 help='ID of the action execution.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        raise NotImplementedError

    def run_and_print(self, args):
        raise NotImplementedError
