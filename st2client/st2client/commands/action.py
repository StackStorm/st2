import logging

from st2client import models
from st2client.models import action
from st2client.commands import resource
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, manager, description,
                 subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            action.Action, manager, description, subparsers,
            parent_parser=parent_parser, override_help=ActionHelpCommand)

        # Assigns resource and manager to the help command after init.
        self.commands['help'].resource = self.resource
        self.commands['help'].manager = self.manager

        # Registers extended commands
        self.commands['execute'] = ActionExecuteCommand(
            self.resource, self.manager, self.subparsers)


class ActionHelpCommand(resource.ResourceCommand):

    def __init__(self, subparsers, commands):
        # The __init__ method of ActionHelpCommand follows the same signature
        # as the basic HelpCommand. This is required so the command Branch
        # can generically and consistently assign any override help command.
        # Therefore, NoneType is passed to resource and manager in the call
        # to the parent's __init__ below. The ActionBranch above will assign
        # the resource and manager after the ActionHelpCommand has been setup.
        super(ActionHelpCommand, self).__init__(
            'help', 'Print usage for the given command or action.',
            None, None, subparsers)
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

    def __init__(self, resource, manager, subparsers):
        super(ActionExecuteCommand, self).__init__(
            'execute', 'Execute an action manually.',
            resource, manager, subparsers)
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
        # TODO: Figure out how to pass multiple resource managers.
        action_exec_mgr = models.ResourceManager(
            action.ActionExecution, self.manager.endpoint) 
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

    def __init__(self, manager, description,
                 subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            action.ActionExecution, manager, description, subparsers,
            parent_parser=parent_parser, id_by_name=False,
            list_attr=['id', 'action.name', 'status'],
            read_only=True)

        # Registers extended commands
        self.commands['cancel'] = ActionExecutionCancelCommand(
            self.resource, self.manager, self.subparsers)


class ActionExecutionCancelCommand(resource.ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ActionExecutionCancelCommand, self).__init__(
            'cancel', 'Cancels an %s.' % resource.get_display_name().lower(),
            resource, manager, subparsers)
        self.parser.add_argument('execution-id',
                                 help='ID of the action execution.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        raise NotImplementedError
