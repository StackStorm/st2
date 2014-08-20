import ast
import copy
import json
import logging
import textwrap
import time
import sys

from st2common.models.api import action as act

from st2client import models
from st2client.commands import resource
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            models.Action, description, app, subparsers,
            parent_parser=parent_parser)

        # Registers extended commands
        self.commands['execute'] = ActionRunCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class ActionRunCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):

        super(ActionRunCommand, self).__init__(
            resource, kwargs.pop('name', 'execute'),
            'A command to invoke an action manually.',
            *args, **kwargs)

        self.parser.add_argument('name_or_id', nargs='?',
                                 metavar='name-or-id',
                                 help='Name or ID of the action.')
        self.parser.add_argument('parameters', nargs='*',
                                 help='List of keyword args, positional args, '
                                      'and optional args for the action.')

        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

        if self.name == 'run':
            self.parser.add_argument('-a', '--async',
                                     action='store_true', dest='async',
                                     help='Do not wait for action to finish.')
        else:
            self.parser.set_defaults(async=True)

    def run(self, args, **kwargs):
        if not args.name_or_id:
            self.parser.error('too few arguments')

        action = self.get_resource(args.name_or_id)
        if not action:
            raise resource.ResourceNotFoundError('Action "%s" cannot be found.'
                                                 % args.name_or_id)

        runner_mgr = self.app.client.managers['RunnerType']
        runner = runner_mgr.get_by_name(action.runner_type)
        if not runner:
            raise resource.ResourceNotFoundError('Runner type "%s" for action "%s" cannot be found.'
                                                 % (action.runner_type, action.name))

        transformer = {
            'array': list,
            'boolean': (lambda x: ast.literal_eval(x.capitalize())),
            'integer': int,
            'number': float,
            'object': json.loads,
            'string': str
        }

        def normalize(name, value):
            if name in runner.runner_parameters:
                param = runner.runner_parameters[name]
                if 'type' in param and param['type'] in transformer:
                    return transformer[param['type']](value)
            if name in action.parameters:
                param = action.parameters[name]
                if 'type' in param and param['type'] in transformer:
                    return transformer[param['type']](value)
            return value

        execution = models.ActionExecution()
        execution.action = {'name': action.name}
        execution.parameters = dict()
        for idx in range(len(args.parameters)):
            arg = args.parameters[idx]
            if '=' in arg:
                k, v = arg.split('=')
                execution.parameters[k] = normalize(k, v)
            else:
                execution.parameters['cmd'] = ' '.join(args.parameters[idx:])
                break

        action_exec_mgr = self.app.client.managers['ActionExecution']
        execution = action_exec_mgr.create(execution)

        if not args.async:
            while execution.status == act.ACTIONEXEC_STATUS_SCHEDULED \
                    or execution.status == act.ACTIONEXEC_STATUS_RUNNING:
                time.sleep(1)
                sys.stdout.write('.')
                execution = action_exec_mgr.get_by_id(execution.id)

            sys.stdout.write('\n')

            try:
                execution.result = json.loads(execution.result)
            except:
                pass

        return execution

    @staticmethod
    def print_param(name, schema):
        wrapper = textwrap.TextWrapper(width=78)
        wrapper.initial_indent = ' ' * 4
        wrapper.subsequent_indent = wrapper.initial_indent
        print(wrapper.fill(name))
        wrapper.initial_indent = ' ' * 8
        wrapper.subsequent_indent = wrapper.initial_indent
        if 'description' in schema and schema['description']:
            print(wrapper.fill(schema['description']))
        if 'type' in schema and schema['type']:
            print(wrapper.fill('Type: %s' % schema['type']))
        if 'enum' in schema and schema['enum']:
            print(wrapper.fill('Enum: %s' % ', '.join(schema['enum'])))
        if 'default' in schema and schema['default']:
            print(wrapper.fill('Default: %s' % schema['default']))
        print('')

    def print_help(self, args):
        # Print appropriate help message if the help option is given.
        if args.help:
            if args.name_or_id:
                try:
                    action = self.get_resource(args.name_or_id)
                    runner_mgr = self.app.client.managers['RunnerType']
                    runner = runner_mgr.get_by_name(action.runner_type)
                    parameters = copy.copy(runner.runner_parameters)
                    parameters.update(copy.copy(action.parameters))
                    required = (getattr(runner, 'required_parameters', list()) +
                                getattr(action, 'required_parameters', list()))
                    print('')
                    print(textwrap.fill(action.description))
                    print('')
                    if set(parameters.keys()) & set(required):
                        print('Required Parameters:')
                        [self.print_param(name, parameters.get(name))
                         for name in sorted(parameters) if name in required]
                    if set(parameters.keys()) - set(required):
                        print('Optional Parameters:')
                        [self.print_param(name, parameters.get(name))
                        for name in sorted(parameters) if name not in required]
                except resource.ResourceNotFoundError:
                    print('Action "%s" is not found.' % args.name_or_id)
                except Exception as e:
                    print('ERROR: Unable to print help for action "%s". %s' %
                          (args.name_or_id, e.message))
            else:
                self.parser.print_help()
            return True
        return False

    def run_and_print(self, args, **kwargs):
        if self.print_help(args):
            return
        # Execute the action.
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)
        if args.async:
            self.print_output('To get the results, execute: \n'
                              '    $ st2 execution get %s' % instance.id,
                              unicode)


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            models.ActionExecution, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={'list': ActionExecutionListCommand,
                      'get': ActionExecutionGetCommand})

        # Registers extended commands
        self.commands['cancel'] = ActionExecutionCancelCommand(
            self.resource, self.app, self.subparsers)


class ActionExecutionListCommand(resource.ResourceCommand):

    display_attributes = ['id', 'action.name', 'status', 'start_timestamp']

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionListCommand, self).__init__(
            resource, 'list', 'Get the list of the 50 most recent %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('--action-name', help='Action name to filter the list.')
        self.group.add_argument('--action-id', help='Action id to filter the list.')
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=50,
                                 help=('List N most recent %s; '
                                       'list all if 0.' %
                                       resource.get_plural_display_name().lower()))
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
        filters = dict()
        if args.action_name:
            filters['action_name'] = args.action_name
        elif args.action_id:
            filters['action_id'] = args.action_id
        return (self.manager.query(limit=args.last, **filters)
                if filters else self.manager.get_all(limit=args.last))

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(instances, table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json)


class ActionExecutionGetCommand(resource.ResourceCommand):

    display_attributes = ['all']

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionGetCommand, self).__init__(
            resource, 'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('id',
                                 help=('ID of the %s.' %
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
        return self.manager.get_by_id(args.id)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)


class ActionExecutionCancelCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionCancelCommand, self).__init__(
            resource, 'cancel',
            'Cancels an %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('execution-id',
                                 help='ID of the action execution.')
        self.parser.add_argument('-j', '--json',
                                 action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args, **kwargs):
        raise NotImplementedError

    def run_and_print(self, args, **kwargs):
        raise NotImplementedError
