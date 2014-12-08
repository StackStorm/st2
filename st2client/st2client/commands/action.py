# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import ast
import copy
import json
import logging
import textwrap
import time
import six
import sys

from os.path import join as pjoin

from st2client import models
from st2client.commands import resource
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.formatters import table, execution
from st2client.utils.date import format_isodate


LOG = logging.getLogger(__name__)

ACTIONEXEC_STATUS_SCHEDULED = 'scheduled'
ACTIONEXEC_STATUS_RUNNING = 'running'


class ActionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            models.Action, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': ActionListCommand,
                'get': ActionGetCommand,
                'update': ActionUpdateCommand,
                'delete': ActionDeleteCommand
            })

        # Registers extended commands
        self.commands['execute'] = ActionRunCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class ActionListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'name', 'description']


class ActionGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'entry_point', 'runner_type',
                               'parameters']


class ActionUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class ActionDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass


class ActionRunCommand(resource.ResourceCommand):
    attribute_display_order = ['id', 'ref', 'context', 'parameters', 'status',
                               'start_timestamp', 'result']

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
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)

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

        def read_file(file_path):
            if not os.path.exists(file_path):
                raise ValueError('File "%s" doesn\'t exist' % (file_path))

            if not os.path.isfile(file_path):
                raise ValueError('"%s" is not a file' % (file_path))

            with open(file_path, 'rb') as fp:
                content = fp.read()

            return content

        transformer = {
            'array': (lambda cs_x: [v.strip() for v in cs_x.split(',')]),
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

        action_ref = '.'.join([action.pack, action.name])
        execution = models.ActionExecution()
        execution.action = action_ref
        execution.parameters = dict()
        for idx in range(len(args.parameters)):
            arg = args.parameters[idx]
            if '=' in arg:
                k, v = arg.split('=', 1)

                # Attribute for files are prefixed with "@"
                if k.startswith('@'):
                    k = k[1:]
                    is_file = True
                else:
                    is_file = False

                try:
                    if is_file:
                        # Files are handled a bit differently since we ship the content
                        # over the wire
                        file_path = os.path.normpath(pjoin(os.getcwd(), v))
                        file_name = os.path.basename(file_path)
                        content = read_file(file_path=file_path)
                        execution.parameters['_file_name'] = file_name
                        execution.parameters['file_content'] = content
                    else:
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

        if 'file_content' in execution.parameters:
            if 'method' not in execution.parameters:
                # Default to POST if a method is not provided
                execution.parameters['method'] = 'POST'

            if 'file_name' not in execution.parameters:
                # File name not provided, use default file name
                execution.parameters['file_name'] = execution.parameters['_file_name']

            del execution.parameters['_file_name']

        action_exec_mgr = self.app.client.managers['ActionExecution']
        execution = action_exec_mgr.create(execution, **kwargs)

        if not args.async:
            while execution.status == ACTIONEXEC_STATUS_SCHEDULED \
                    or execution.status == ACTIONEXEC_STATUS_RUNNING:
                time.sleep(1)
                if not args.json:
                    sys.stdout.write('.')
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            sys.stdout.write('\n')

            if self._is_error_result(result=execution.result):
                execution.result = self._format_error_result(execution.result)

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
        if 'default' in schema and schema['default'] is not None:
            print(wrapper.fill('Default: %s' % schema['default']))
        print('')

    @staticmethod
    def _get_params_types(runner, action):
        runner_params = runner.runner_parameters
        action_params = action.parameters
        parameters = copy.copy(runner_params)
        parameters.update(copy.copy(action_params))
        required = set([k for k, v in six.iteritems(parameters) if v.get('required')])

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
                    parameters, required, optional, _ = self._get_params_types(runner,
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
                          attributes=['all'], json=args.json,
                          attribute_display_order=self.attribute_display_order)
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

    def _is_error_result(self, result):
        if not isinstance(result, dict):
            return False

        if 'message' not in result:
            return False

        if 'traceback' not in result:
            return False

        return True

    def _format_error_result(self, result):
        result = 'Message: %s\nTraceback: %s' % (result['message'],
                result['traceback'])
        return result


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            models.ActionExecution, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={'list': ActionExecutionListCommand,
                      'get': ActionExecutionGetCommand})


class ActionExecutionListCommand(resource.ResourceCommand):

    display_attributes = ['id', 'action', 'context.user', 'status', 'start_timestamp',
                          'end_timestamp']
    attribute_transform_functions = {
        'start_timestamp': format_isodate,
        'end_timestamp': format_isodate
    }

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionListCommand, self).__init__(
            resource, 'list', 'Get the list of the 50 most recent %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('--action', help='Action reference to filter the list.')
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
        if args.action:
            kwargs['action'] = args.action
        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(reversed(instances), table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json,
                          attribute_transform_functions=self.attribute_transform_functions)


class ActionExecutionGetCommand(resource.ResourceCommand):

    display_attributes = ['all']
    attribute_transform_functions = {
        'start_timestamp': format_isodate,
        'end_timestamp': format_isodate
    }

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionGetCommand, self).__init__(
            resource, 'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('id',
                                 help=('ID of the %s.' %
                                       resource.get_display_name().lower()))

        root_arg_grp = self.parser.add_mutually_exclusive_group()

        detail_arg_grp = root_arg_grp.add_mutually_exclusive_group()
        detail_arg_grp.add_argument('-a', '--attr', nargs='+',
                                    default=self.display_attributes,
                                    help=('List of attributes to include in the '
                                          'output. "all" or unspecified will '
                                          'return all attributes.'))
        detail_arg_grp.add_argument('-d', '--detail', action='store_true',
                                    help='Display full detail of the execution in table format.')

        result_arg_grp = root_arg_grp.add_mutually_exclusive_group()
        result_arg_grp.add_argument('-k', '--key',
                                    help=('If result is type of JSON, then print specific '
                                          'key-value pair; dot notation for nested JSON is '
                                          'supported.'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.get_by_id(args.id, **kwargs)

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            formatter = table.PropertyValueTable if args.detail else execution.ExecutionResult
            if args.detail:
                options = {'attributes': args.attr}
            elif args.key:
                options = {'attributes': ['result.%s' % args.key], 'key': args.key}
            else:
                options = {'attributes': ['status', 'result']}
            options['json'] = args.json
            options['attribute_transform_functions'] = self.attribute_transform_functions
            self.print_output(instance, formatter, **options)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)
