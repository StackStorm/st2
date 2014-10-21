import ast
import copy
import json
import logging
import textwrap
import time
import six
import sys

from st2common.models.api import action as act

from st2client import models
from st2client.commands import resource
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.formatters import table


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            models.Action, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': ActionListCommand
            })

        # Registers extended commands
        self.commands['execute'] = ActionRunCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class ActionListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'content_pack', 'name', 'description']


class ActionRunCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):

        super(ActionRunCommand, self).__init__(
            resource, kwargs.pop('name', 'execute'),
            'A command to invoke an action manually.',
            *args, **kwargs)

        self.parser.add_argument('ref_or_id', nargs='?',
                                 metavar='ref-or-id',
                                 help='Fully qualified name (pack.action_name) ' +
                                 'or ID of the action.')
        self.parser.add_argument('parameters', nargs='*',
                                 help='List of keyword args, positional args, '
                                      'and optional args for the action.')

        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')

        if self.name == 'run':
            self.parser.add_argument('-a', '--async',
                                     action='store_true', dest='async',
                                     help='Do not wait for action to finish.')
        else:
            self.parser.set_defaults(async=True)

    def get_resource(self, ref_or_id, **kwargs):
        query_params = {'ref': ref_or_id}
        instance = self.manager.query(**query_params)[0]
        if not instance:
            try:
                instance = self.manager.get_by_id(ref_or_id, **kwargs)
            except:
                pass
        if not instance:
            message = ('Resource with id or name "%s" doesn\'t exist.' %
                       (ref_or_id))
            raise resource.ResourceNotFoundError(message)
        return instance

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if not args.ref_or_id:
            self.parser.error('too few arguments')

        action = self.get_resource(args.ref_or_id, **kwargs)
        if not action:
            raise resource.ResourceNotFoundError('Action "%s" cannot be found.'
                                                 % args.ref_or_id)

        runner_mgr = self.app.client.managers['RunnerType']
        runner = runner_mgr.get_by_name(action.runner_type, **kwargs)
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

        action_ref = '.'.join([action.content_pack, action.name])
        execution = models.ActionExecution()
        execution.ref = action_ref
        execution.parameters = dict()
        for idx in range(len(args.parameters)):
            arg = args.parameters[idx]
            if '=' in arg:
                k, v = arg.split('=')
                try:
                    execution.parameters[k] = normalize(k, v)
                except Exception as e:
                    # TODO: Move transformers in a separate module and handle
                    # exceptions there
                    if 'malformed string' in str(e):
                        message = ('Invalid value for boolean parameter. '
                                   'Valid values are: true, false')
                        raise ValueError(message)
                    else:
                        raise e
            else:
                execution.parameters['cmd'] = ' '.join(args.parameters[idx:])
                break

        action_exec_mgr = self.app.client.managers['ActionExecution']
        execution = action_exec_mgr.create(execution, **kwargs)

        if not args.async:
            while execution.status == act.ACTIONEXEC_STATUS_SCHEDULED \
                    or execution.status == act.ACTIONEXEC_STATUS_RUNNING:
                time.sleep(1)
                if not args.json:
                    sys.stdout.write('.')
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            sys.stdout.write('\n')

            try:
                execution.result = json.loads(execution.result)
            except:
                pass

        return execution

    @staticmethod
    def print_param(name, schema):
        if not schema:
            raise ValueError('Missing schema for parameter "%s"' % (name))

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

    @staticmethod
    def _get_params_types(runner, action):
        runner_params = runner.runner_parameters
        action_params = action.parameters
        parameters = copy.copy(runner_params)
        parameters.update(copy.copy(action_params))
        required = set((getattr(runner, 'required_parameters', list()) +
                        getattr(action, 'required_parameters', list())))

        def is_immutable(runner_param_meta, action_param_meta):
            # If runner sets a param as immutable, action cannot override that.
            if runner_param_meta.get('immutable', False):
                return True
            else:
                return action_param_meta.get('immutable', False)

        immutable = set()
        for param in parameters.keys():
            if is_immutable(runner_params.get(param, {}),
                            action_params.get(param, {})):
                immutable.add(param)

        required = required - immutable
        optional = set(parameters.keys()) - required - immutable

        return parameters, required, optional, immutable

    @add_auth_token_to_kwargs_from_cli
    def print_help(self, args, **kwargs):
        # Print appropriate help message if the help option is given.
        if args.help:
            if args.ref_or_id:
                try:
                    action = self.get_resource(args.ref_or_id, **kwargs)
                    runner_mgr = self.app.client.managers['RunnerType']
                    runner = runner_mgr.get_by_name(action.runner_type, **kwargs)
                    parameters, required, optional, immutable = self._get_params_types(runner,
                                                                                       action)
                    print('')
                    print(textwrap.fill(action.description))
                    print('')
                    if required:
                        required = self._sort_parameters(parameters=parameters,
                                                         names=required)

                        print('Required Parameters:')
                        [self.print_param(name, parameters.get(name))
                            for name in required]
                    if optional:
                        optional = self._sort_parameters(parameters=parameters,
                                                         names=optional)

                        print('Optional Parameters:')
                        [self.print_param(name, parameters.get(name))
                            for name in optional]
                    if immutable:
                        immutable = self._sort_parameters(parameters=parameters,
                                                          names=immutable)

                        print('Immutable parameters:')
                        [self.print_param(name, parameters.get(name))
                            for name in immutable]
                except resource.ResourceNotFoundError:
                    print('Action "%s" is not found.' % args.ref_or_id)
                except Exception as e:
                    print('ERROR: Unable to print help for action "%s". %s' %
                          (args.ref_or_id, e))
            else:
                self.parser.print_help()
            return True
        return False

    def run_and_print(self, args, **kwargs):
        if self.print_help(args, **kwargs):
            return
        # Execute the action.
        instance = self.run(args, **kwargs)
        self.print_output(instance, table.PropertyValueTable,
                          attributes=['all'], json=args.json)
        if args.async:
            self.print_output('To get the results, execute: \n'
                              '    $ st2 execution get %s' % instance.id,
                              six.text_type)

    def _sort_parameters(self, parameters, names):
        """
        Sort a provided list of action parameters.

        :type parameters: ``list``
        :type names: ``list`` or ``set``
        """
        sorted_parameters = sorted(names, key=lambda name:
                                   self._get_parameter_sort_value(
                                       parameters=parameters,
                                       name=name))

        return sorted_parameters

    def _get_parameter_sort_value(self, parameters, name):
        """
        Return a value which determines sort order for a particular parameter.

        By default, parameters are sorted using "position" parameter attribute.
        If this attribute is not available, parameter is sorted based on the
        name.
        """
        parameter = parameters.get(name, None)

        if not parameter:
            return None

        sort_value = parameter.get('position', name)
        return sort_value


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            models.ActionExecution, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={'list': ActionExecutionListCommand,
                      'get': ActionExecutionGetCommand})


class ActionExecutionListCommand(resource.ResourceCommand):

    display_attributes = ['id', 'action.name', 'context.user', 'status', 'start_timestamp']

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

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if args.action_name:
            kwargs['action_name'] = args.action_name
        elif args.action_id:
            kwargs['action_id'] = args.action_id
        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        if len(instances) == 1:
            attr = (args.attr
                    if (set(args.attr) - set(self.display_attributes) or
                        set(self.display_attributes) - set(args.attr))
                    else ['all'])
            self.print_output(instances[0], table.PropertyValueTable,
                              attributes=attr, json=args.json)
        else:
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

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.get_by_id(args.id, **kwargs)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            self.print_output(instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)
