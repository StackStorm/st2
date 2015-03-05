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
from st2client.exceptions.operations import OperationFailureException
from st2client.formatters import table
from st2client.formatters import execution as execution_formatter
from st2client.utils import jsutil
from st2client.utils.date import format_isodate
from st2client.utils.color import format_status

LOG = logging.getLogger(__name__)

LIVEACTION_STATUS_SCHEDULED = 'scheduled'
LIVEACTION_STATUS_RUNNING = 'running'

# Who parameters should be masked when displaying action execution output
PARAMETERS_TO_MASK = [
    'password',
    'private_key'
]

# A list of environment variables which are never inherited when using run
# --inherit-env flag
ENV_VARS_BLACKLIST = [
    'pwd',
    'mail',
    'username',
    'user',
    'path',
    'home',
    'ps1',
    'shell',
    'pythonpath',
    'ssh_tty',
    'ssh_connection',
    'lang',
    'ls_colors',
    'logname',
    'oldpwd',
    'term',
    'xdg_session_id'
]

WORKFLOW_RUNNER_TYPES = [
    'action-chain',
    'mistral-v1',
    'mistral-v2',
]


def format_parameters(value):
    # Mask sensitive parameters
    if not isinstance(value, dict):
        # No parameters, leave it as it is
        return value

    for param_name, _ in value.items():
        if param_name in PARAMETERS_TO_MASK:
            value[param_name] = '********'

    return value

# String for indenting etc.
WF_PREFIX = '+ '
NON_WF_PREFIX = '  '
INDENT_CHAR = ' '


def format_wf_instances(instances):
    """
    Adds identification characters to a workflow and appropriately shifts
    the non-workflow instances. If no workflows are found does nothing.
    """
    # only add extr chars if there are workflows.
    has_wf = False
    for instance in instances:
        if not getattr(instance, 'children', None):
            continue
        else:
            has_wf = True
            break
    if not has_wf:
        return instances
    # Prepend wf and non_wf prefixes.
    for instance in instances:
        if getattr(instance, 'children', None):
            instance.id = WF_PREFIX + instance.id
        else:
            instance.id = NON_WF_PREFIX + instance.id
    return instances


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


class ActionRunCommandMixin(object):
    """
    Mixin class which contains utility functions related to action execution.
    """
    display_attributes = ['id', 'action.ref', 'context.user', 'parameters', 'status',
                          'start_timestamp', 'end_timestamp', 'result']
    attribute_display_order = ['id', 'action.ref', 'context.user', 'parameters', 'status',
                               'start_timestamp', 'end_timestamp', 'result']
    attribute_transform_functions = {
        'start_timestamp': format_isodate,
        'end_timestamp': format_isodate,
        'parameters': format_parameters,
        'status': format_status
    }

    poll_interval = 2  # how often to poll for execution completion when using sync mode

    def get_resource(self, ref_or_id, **kwargs):
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)

    def run_and_print(self, args, **kwargs):
        if self._print_help(args, **kwargs):
            return

        execution = self.run(args, **kwargs)
        if args.async:
            self.print_output('To get the results, execute:\n st2 execution get %s' %
                              (execution.id), six.text_type)
        else:
            return self._print_execution_details(execution=execution, args=args, **kwargs)

    def _add_common_options(self):
        root_arg_grp = self.parser.add_mutually_exclusive_group()

        # Display options
        task_list_arg_grp = root_arg_grp.add_argument_group()
        task_list_arg_grp.add_argument('--raw', action='store_true',
                                       help='Raw output, don\'t shot sub-tasks for workflows.')
        task_list_arg_grp.add_argument('--tasks', action='store_true',
                                       help='Whether to show sub-tasks of an execution.')
        task_list_arg_grp.add_argument('--depth', type=int, default=-1,
                                       help='Depth to which to show sub-tasks. \
                                             By default all are shown.')
        task_list_arg_grp.add_argument('-w', '--width', nargs='+', type=int, default=None,
                                       help='Set the width of columns in output.')

        execution_details_arg_grp = root_arg_grp.add_mutually_exclusive_group()

        detail_arg_grp = execution_details_arg_grp.add_mutually_exclusive_group()
        detail_arg_grp.add_argument('--attr', nargs='+',
                                    default=['id', 'status', 'result'],
                                    help=('List of attributes to include in the '
                                          'output. "all" or unspecified will '
                                          'return all attributes.'))
        detail_arg_grp.add_argument('-d', '--detail', action='store_true',
                                    help='Display full detail of the execution in table format.')

        result_arg_grp = execution_details_arg_grp.add_mutually_exclusive_group()
        result_arg_grp.add_argument('-k', '--key',
                                    help=('If result is type of JSON, then print specific '
                                          'key-value pair; dot notation for nested JSON is '
                                          'supported.'))

        return root_arg_grp

    def _print_execution_details(self, execution, args, **kwargs):
        """
        Print the execution detail to stdout.

        This method takes into account if an executed action was workflow or not
        and formats the output accordingly.
        """
        runner_type = execution.action.get('runner_type', 'unknown')
        is_workflow_action = runner_type in WORKFLOW_RUNNER_TYPES

        tasks = getattr(args, 'tasks', False)
        raw = getattr(args, 'raw', False)
        detail = getattr(args, 'detail', False)
        key = getattr(args, 'key', None)
        attr = getattr(args, 'attr', [])

        if tasks and not is_workflow_action:
            raise ValueError('--tasks option can only be used with workflow actions')

        if not raw and not detail and (tasks or is_workflow_action):
            self._run_and_print_child_task_list(execution=execution, args=args, **kwargs)
        else:
            instance = execution

            if detail:
                formatter = table.PropertyValueTable
            else:
                formatter = execution_formatter.ExecutionResult

            if detail:
                options = {'attributes': copy.copy(self.display_attributes)}
            elif key:
                options = {'attributes': ['result.%s' % (key)], 'key': key}
            else:
                options = {'attributes': attr}

            options['json'] = args.json
            options['attribute_transform_functions'] = self.attribute_transform_functions
            self.print_output(instance, formatter, **options)

    def _run_and_print_child_task_list(self, execution, args, **kwargs):
        action_exec_mgr = self.app.client.managers['LiveAction']

        # print root task.
        instance = execution
        options = {'attributes': ['id', 'action.ref', 'status', 'start_timestamp',
                                  'end_timestamp']}
        options['json'] = args.json
        options['attribute_transform_functions'] = self.attribute_transform_functions
        formatter = execution_formatter.ExecutionResult
        self.print_output(instance, formatter, **options)

        # print child tasks
        kwargs['depth'] = args.depth
        child_instances = action_exec_mgr.get_property(execution.id, 'children')
        child_instances = self._format_child_instances(child_instances, execution.id)
        self.print_output(child_instances, table.MultiColumnTable,
                          attributes=['id', 'status', 'task', 'action', 'start_timestamp'],
                          widths=args.width, json=args.json,
                          attribute_transform_functions=self.attribute_transform_functions)

    def _get_execution_result(self, execution, action_exec_mgr, args, **kwargs):
        pending_statuses = [LIVEACTION_STATUS_SCHEDULED, LIVEACTION_STATUS_RUNNING]

        if not args.async:
            while execution.status in pending_statuses:
                time.sleep(self.poll_interval)
                if not args.json:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            sys.stdout.write('\n')

            if self._is_error_result(result=execution.result):
                execution.result = self._format_error_result(execution.result)

        return execution

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

    def _get_action_parameters_from_args(self, action, runner, args):
        """
        Build a dictionary with parameters which will be passed to the action by
        parsing parameters passed to the CLI.

        :param args: CLI argument.
        :type args: ``object``

        :rtype: ``dict``
        """
        action_ref_or_id = action.ref

        def read_file(file_path):
            if not os.path.exists(file_path):
                raise ValueError('File "%s" doesn\'t exist' % (file_path))

            if not os.path.isfile(file_path):
                raise ValueError('"%s" is not a file' % (file_path))

            with open(file_path, 'rb') as fp:
                content = fp.read()

            return content

        def transform_object(value):
            # Also support simple key1=val1,key2=val2 syntax
            if value.startswith('{'):
                # Assume it's JSON
                result = value = json.loads(value)
            else:
                pairs = value.split(',')

                result = {}
                for pair in pairs:
                    split = pair.split('=', 1)

                    if len(split) != 2:
                        continue

                    key, value = split
                    result[key] = value
            return result

        transformer = {
            'array': (lambda cs_x: [v.strip() for v in cs_x.split(',')]),
            'boolean': (lambda x: ast.literal_eval(x.capitalize())),
            'integer': int,
            'number': float,
            'object': transform_object,
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

        result = {}
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

                        if action_ref_or_id == 'core.http':
                            # Special case for http runner
                            result['_file_name'] = file_name
                            result['file_content'] = content
                        else:
                            result[k] = content
                    else:
                        result[k] = normalize(k, v)
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
                result['cmd'] = ' '.join(args.parameters[idx:])
                break

        # Special case for http runner
        if 'file_content' in result:
            if 'method' not in result:
                # Default to POST if a method is not provided
                result['method'] = 'POST'

            if 'file_name' not in result:
                # File name not provided, use default file name
                result['file_name'] = result['_file_name']

            del result['_file_name']

        if args.inherit_env:
            result['env'] = self._get_inherited_env_vars()

        return result

    @add_auth_token_to_kwargs_from_cli
    def _print_help(self, args, **kwargs):
        # Print appropriate help message if the help option is given.
        action_mgr = self.app.client.managers['Action']
        action_exec_mgr = self.app.client.managers['LiveAction']

        if args.help:
            action_ref_or_id = getattr(args, 'ref_or_id', None)
            action_exec_id = getattr(args, 'id', None)

            if action_exec_id and not action_ref_or_id:
                action_exec = action_exec_mgr.get_by_id(action_exec_id, **kwargs)
                args.ref_or_id = action_exec.action

            if action_ref_or_id:
                try:
                    action = action_mgr.get_by_ref_or_id(args.ref_or_id, **kwargs)
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
                        [self._print_param(name, parameters.get(name))
                            for name in required]
                    if optional:
                        optional = self._sort_parameters(parameters=parameters,
                                                         names=optional)

                        print('Optional Parameters:')
                        [self._print_param(name, parameters.get(name))
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

    @staticmethod
    def _print_param(name, schema):
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

    def _format_child_instances(self, children, parent_id):
        '''
        The goal of this method is to add an indent at every level. This way the
        WF is represented as a tree structure while in a list. For the right visuals
        representation the list must be a DF traversal else the idents will end up
        looking strange.
        '''
        # apply basic WF formating first.
        children = format_wf_instances(children)
        # setup a depth lookup table
        depth = {parent_id: 0}
        result = []
        # main loop that indents each entry correctly
        for child in children:
            # make sure child.parent is in depth and while at it compute the
            # right depth for indentation purposes.
            if child.parent not in depth:
                parent = None
                for instance in children:
                    if WF_PREFIX in instance.id:
                        instance_id = instance.id[instance.id.index(WF_PREFIX) + len(WF_PREFIX):]
                    else:
                        instance_id = instance.id
                    if instance_id == child.parent:
                        parent = instance
                if parent and parent.parent and parent.parent in depth:
                    depth[child.parent] = depth[parent.parent] + 1
                else:
                    depth[child.parent] = 0
            # now ident for the right visuals
            child.id = INDENT_CHAR * depth[child.parent] + child.id
            result.append(self._format_for_common_representation(child))
        return result

    def _format_for_common_representation(self, task):
        '''
        Formats a task for common representation between mistral and action-chain.
        '''
        # This really needs to be better handled on the back-end but that would be a bigger
        # change so handling in cli.
        context = getattr(task, 'context', None)
        if context and 'chain' in context:
            task_name_key = 'context.chain.name'
        elif context and 'mistral' in context:
            task_name_key = 'context.mistral.task_name'
        # Use LiveAction as the object so that the formatter lookup does not change.
        # AKA HACK!
        return models.action.LiveAction(**{
            'id': task.id,
            'status': task.status,
            'task': jsutil.get_value(vars(task), task_name_key),
            'action': task.action.get('ref', None),
            'start_timestamp': task.start_timestamp
        })

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

    def _get_inherited_env_vars(self):
        env_vars = os.environ.copy()

        for var_name in ENV_VARS_BLACKLIST:
            if var_name.lower() in env_vars:
                del env_vars[var_name.lower()]
            if var_name.upper() in env_vars:
                del env_vars[var_name.upper()]

        return env_vars


class ActionRunCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):

        super(ActionRunCommand, self).__init__(
            resource, kwargs.pop('name', 'execute'),
            'A command to invoke an action manually.',
            *args, **kwargs)

        self.parser.add_argument('ref_or_id', nargs='?',
                                 metavar='ref-or-id',
                                 help='Action reference (pack.action_name) ' +
                                 'or ID of the action.')
        self.parser.add_argument('parameters', nargs='*',
                                 help='List of keyword args, positional args, '
                                      'and optional args for the action.')

        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')

        self._add_common_options()

        if self.name in ['run', 'execute']:
            self.parser.add_argument('-a', '--async',
                                     action='store_true', dest='async',
                                     help='Do not wait for action to finish.')
            self.parser.add_argument('-e', '--inherit-env',
                                     action='store_true', dest='inherit_env',
                                     help='Pass all the environment variables '
                                          'which are accessible to the CLI as "env" '
                                          'parameter to the action. Note: Only works '
                                          'with python, local and remote runners.')

        if self.name == 'run':
            self.parser.set_defaults(async=False)
        else:
            self.parser.set_defaults(async=True)

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if not args.ref_or_id:
            self.parser.error('Missing action reference or id')

        action = self.get_resource(args.ref_or_id, **kwargs)
        if not action:
            raise resource.ResourceNotFoundError('Action "%s" cannot be found.'
                                                 % (args.ref_or_id))

        runner_mgr = self.app.client.managers['RunnerType']
        runner = runner_mgr.get_by_name(action.runner_type, **kwargs)
        if not runner:
            raise resource.ResourceNotFoundError('Runner type "%s" for action "%s" cannot be found.'
                                                 % (action.runner_type, action.name))

        action_ref = '.'.join([action.pack, action.name])
        action_parameters = self._get_action_parameters_from_args(action=action, runner=runner,
                                                                  args=args)

        execution = models.LiveAction()
        execution.action = action_ref
        execution.parameters = action_parameters

        action_exec_mgr = self.app.client.managers['LiveAction']

        execution = action_exec_mgr.create(execution, **kwargs)
        execution = self._get_execution_result(execution=execution,
                                               action_exec_mgr=action_exec_mgr,
                                               args=args, **kwargs)
        return execution


class ActionExecutionBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            models.LiveAction, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={'list': ActionExecutionListCommand,
                      'get': ActionExecutionGetCommand})

        # Register extended commands
        self.commands['re-run'] = ActionExecutionReRunCommand(self.resource, self.app,
                                                              self.subparsers, add_help=False)


POSSIBLE_ACTION_STATUS_VALUES = ('succeeded', 'running', 'scheduled', 'failed')


class ActionExecutionListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'action.ref', 'context.user', 'status', 'start_timestamp',
                          'end_timestamp']
    attribute_transform_functions = {
        'start_timestamp': format_isodate,
        'end_timestamp': format_isodate,
        'parameters': format_parameters,
        'status': format_status
    }

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionListCommand, self).__init__(
            resource, 'list', 'Get the list of the 50 most recent %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.group = self.parser.add_argument_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=50,
                                 help=('List N most recent %s; '
                                       'list all if 0.' %
                                       resource.get_plural_display_name().lower()))

        # Filter options
        self.group.add_argument('--action', help='Action reference to filter the list.')
        self.group.add_argument('--status', help=('Only return executions with the provided status.'
                                                  ' Possible values are \'%s\', \'%s\', \'%s\' or'
                                                  ' \'%s\'.' % POSSIBLE_ACTION_STATUS_VALUES))
        self.parser.add_argument('-tg', '--timestamp-gt', type=str, dest='timestamp_gt',
                                 default=None,
                                 help=('Only return executions with timestamp '
                                       'greater than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))
        self.parser.add_argument('-tl', '--timestamp-lt', type=str, dest='timestamp_lt',
                                 default=None,
                                 help=('Only return executions with timestamp '
                                       'lower than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))
        self.parser.add_argument('-l', '--showall', action='store_true',
                                 help='')

        # Display options
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.action:
            kwargs['action'] = args.action
        if args.status:
            kwargs['status'] = args.status
        if not args.showall:
            # null is the magic string that translates to does not exist.
            kwargs['parent'] = 'null'
        if args.timestamp_gt:
            kwargs['timestamp_gt'] = args.timestamp_gt
        if args.timestamp_lt:
            kwargs['timestamp_lt'] = args.timestamp_lt

        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = format_wf_instances(self.run(args, **kwargs))
        self.print_output(reversed(instances), table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json,
                          attribute_transform_functions=self.attribute_transform_functions)


class ActionExecutionGetCommand(ActionRunCommandMixin, resource.ResourceCommand):
    display_attributes = ['id', 'action.ref', 'context.user', 'parameters', 'status',
                          'start_timestamp', 'end_timestamp', 'result', 'liveaction']

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionGetCommand, self).__init__(
            resource, 'get',
            'Get individual %s.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('id',
                                 help=('ID of the %s.' %
                                       resource.get_display_name().lower()))

        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        execution = self.get_resource_by_id(id=args.id, **kwargs)
        return execution

    def run_and_print(self, args, **kwargs):
        try:
            execution = self.run(args, **kwargs)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)
            raise OperationFailureException('Execution %s not found.' % (args.id))

        return self._print_execution_details(execution=execution, args=args, **kwargs)


class ActionExecutionReRunCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):

        super(ActionExecutionReRunCommand, self).__init__(
            resource, kwargs.pop('name', 're-run'),
            'A command to re-run a particular action.',
            *args, **kwargs)

        self.parser.add_argument('id', nargs='?',
                                 metavar='id',
                                 help='ID of action execution to re-run ')
        self.parser.add_argument('parameters', nargs='*',
                                 help='List of keyword args, positional args, '
                                      'and optional args for the action.')
        self.parser.add_argument('-a', '--async',
                                 action='store_true', dest='async',
                                 help='Do not wait for action to finish.')
        self.parser.add_argument('-e', '--inherit-env',
                                 action='store_true', dest='inherit_env',
                                 help='Pass all the environment variables '
                                      'which are accessible to the CLI as "env" '
                                      'parameter to the action. Note: Only works '
                                      'with python, local and remote runners.')
        self.parser.add_argument('-h', '--help',
                                 action='store_true', dest='help',
                                 help='Print usage for the given action.')

        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        existing_execution = self.manager.get_by_id(args.id, **kwargs)

        if not existing_execution:
            raise resource.ResourceNotFoundError('Action execution with id "%s" cannot be found.' %
                                                 (args.id))

        action_mgr = self.app.client.managers['Action']
        runner_mgr = self.app.client.managers['RunnerType']
        action_exec_mgr = self.app.client.managers['LiveAction']

        # TODO use action.ref when this attribute is added
        action_ref = existing_execution.action['ref']
        action = action_mgr.get_by_ref_or_id(action_ref)
        runner = runner_mgr.get_by_name(action.runner_type)

        action_parameters = self._get_action_parameters_from_args(action=action, runner=runner,
                                                                  args=args)

        # Create new execution object
        new_execution = models.LiveAction()
        new_execution.action = action_ref
        new_execution.parameters = getattr(existing_execution, 'parameters', {})

        # If user provides parameters merge and override with the ones from the
        # existing execution
        new_execution.parameters.update(action_parameters)

        execution = action_exec_mgr.create(new_execution, **kwargs)
        execution = self._get_execution_result(execution=execution,
                                               action_exec_mgr=action_exec_mgr,
                                               args=args, **kwargs)
        return execution
