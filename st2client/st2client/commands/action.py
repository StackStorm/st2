import logging

from st2client import models
from st2client.models import action
from st2client.commands import resource
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, description,
                 app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            action.Action, description, app, subparsers,
            parent_parser=parent_parser,
            commands={'help': ActionHelpCommand})

        # Registers extended commands
        self.commands['execute'] = ActionExecuteCommand(
            self.resource, self.app, self.subparsers)


class ActionHelpCommand(resource.ResourceCommand):

    def __init__(self, resource, app, subparsers, commands):
        super(ActionHelpCommand, self).__init__(
            'help', 'Print usage for the given command or action.',
            resource, app, subparsers)
        self.parser.add_argument('command', metavar='command/action',
                                 help='Name of the command or action.')
        self.commands = commands
        self.commands['help'] = self

    def run(self, args):
        if args.command in self.commands:
            command = self.commands[args.command]
            command.parser.print_help()
        else:
            try:
                action = self.manager.get_by_name(args.command)
                print action.description
            except Exception as e:
                print 'Action "%s" is not found.' % args.command
        print


class ActionExecuteCommand(resource.ResourceCommand):

    def __init__(self, resource, app, subparsers):
        super(ActionExecuteCommand, self).__init__(
            'execute', 'Execute an action manually.',
            resource, app, subparsers)
        self.parser.add_argument('name',
                                 help='Name of the action.')
        self.parser.add_argument('-p', '--params', nargs='+',
                                 help='List of parameters (i.e. k1=v1 k2=v2) '
                                      'to pass into the action.')
        self.parser.add_argument('-r', '--runner-params', nargs='+',
                                 help='List of parameters (i.e. k3=v3 k4=v4) '
                                      'to pass into the action runner.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        action_exec_mgr = self.app.client.managers['ActionExecution'] 
        if not self.manager.get_by_name(args.name):
            raise Exception('Action "%s" cannot be found.' % args.name)
        instance = action.ActionExecution()
        instance.action = { "name": args.name }
        instance.action_parameters = {}
        if args.params:
            for kvp in args.params:
                k, v = kvp.split('=')
                instance.action_parameters[k] = v
        instance.runner_parameters = {}
        if args.runner_params:
            for kvp in args.runner_params:
                k, v = kvp.split('=')
                instance.runner_parameters[k] = v
        instance = action_exec_mgr.create(instance)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description,
                 app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            action.ActionExecution, description, app, subparsers,
            parent_parser=parent_parser, id_by_name=False,
            list_attr=['id', 'action.name', 'status'],
            read_only=True, commands={'list': ActionExecutionListCommand})

        # Registers extended commands
        self.commands['cancel'] = ActionExecutionCancelCommand(
            self.resource, self.app, self.subparsers)


class ActionExecutionListCommand(resource.ResourceCommand):

    def __init__(self, resource, app, subparsers, attributes=['all']):
        super(ActionExecutionListCommand, self).__init__(
            'list',
            'Get the list of %s.' % resource.get_plural_display_name().lower(),
            resource, app, subparsers)
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('--action-name',
                                 help='Action name to filter the list.') 
        self.group.add_argument('--action-id',
                                 help='Action id to filter the list.')
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
        filters = dict()
        if args.action_name:
            filters['action_name'] = args.action_name
        elif args.action_id:
            filters['action_id'] = args.action_id
        instances = (self.manager.query(**filters)
                     if filters else self.manager.get_all())
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json)


class ActionExecutionCancelCommand(resource.ResourceCommand):

    def __init__(self, resource, app, subparsers):
        super(ActionExecutionCancelCommand, self).__init__(
            'cancel', 'Cancels an %s.' % resource.get_display_name().lower(),
            resource, app, subparsers)
        self.parser.add_argument('execution-id',
                                 help='ID of the action execution.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        raise NotImplementedError
