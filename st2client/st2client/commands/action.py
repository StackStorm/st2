import logging

from st2client.commands import resource
from st2client.models import action


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
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        raise NotImplementedError
