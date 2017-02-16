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
import calendar
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
from st2client.utils.date import format_isodate_for_user_timezone
from st2client.utils.date import parse as parse_isotime
from st2client.utils.color import format_status

LOG = logging.getLogger(__name__)

LIVEACTION_STATUS_REQUESTED = 'requested'
LIVEACTION_STATUS_SCHEDULED = 'scheduled'
LIVEACTION_STATUS_DELAYED = 'delayed'
LIVEACTION_STATUS_RUNNING = 'running'
LIVEACTION_STATUS_SUCCEEDED = 'succeeded'
LIVEACTION_STATUS_FAILED = 'failed'
LIVEACTION_STATUS_TIMED_OUT = 'timeout'
LIVEACTION_STATUS_ABANDONED = 'abandoned'
LIVEACTION_STATUS_CANCELING = 'canceling'
LIVEACTION_STATUS_CANCELED = 'canceled'


LIVEACTION_COMPLETED_STATES = [
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
    LIVEACTION_STATUS_TIMED_OUT,
    LIVEACTION_STATUS_CANCELED,
    LIVEACTION_STATUS_ABANDONED
]

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


def format_execution_statuses(instances):
    result = []
    for instance in instances:
        instance = format_execution_status(instance)
        result.append(instance)

    return result


def format_execution_status(instance):
    """
    Augment instance "status" attribute with number of seconds which have elapsed for all the
    executions which are in running state and execution total run time for all the executions
    which have finished.
    """
    start_timestamp = getattr(instance, 'start_timestamp', None)
    end_timestamp = getattr(instance, 'end_timestamp', None)

    if instance.status == LIVEACTION_STATUS_RUNNING and start_timestamp:
        start_timestamp = instance.start_timestamp
        start_timestamp = parse_isotime(start_timestamp)
        start_timestamp = calendar.timegm(start_timestamp.timetuple())
        now = int(time.time())
        elapsed_seconds = (now - start_timestamp)
        instance.status = '%s (%ss elapsed)' % (instance.status, elapsed_seconds)
    elif instance.status in LIVEACTION_COMPLETED_STATES and start_timestamp and end_timestamp:
        start_timestamp = parse_isotime(start_timestamp)
        start_timestamp = calendar.timegm(start_timestamp.timetuple())
        end_timestamp = parse_isotime(end_timestamp)
        end_timestamp = calendar.timegm(end_timestamp.timetuple())

        elapsed_seconds = (end_timestamp - start_timestamp)
        instance.status = '%s (%ss elapsed)' % (instance.status, elapsed_seconds)

    return instance


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
        self.commands['enable'] = ActionEnableCommand(self.resource, self.app, self.subparsers)
        self.commands['disable'] = ActionDisableCommand(self.resource, self.app, self.subparsers)
        self.commands['execute'] = ActionRunCommand(
            self.resource, self.app, self.subparsers,
            add_help=False)


class ActionListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description']


class ActionGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'uid', 'ref', 'pack', 'name', 'description',
                               'enabled', 'entry_point', 'runner_type',
                               'parameters']


class ActionUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class ActionEnableCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'entry_point', 'runner_type',
                               'parameters']


class ActionDisableCommand(resource.ContentPackResourceDisableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'description',
                               'enabled', 'entry_point', 'runner_type',
                               'parameters']


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
        'start_timestamp': format_isodate_for_user_timezone,
        'end_timestamp': format_isodate_for_user_timezone,
        'parameters': format_parameters,
        'status': format_status
    }

    poll_interval = 2  # how often to poll for execution completion when using sync mode

    def get_resource(self, ref_or_id, **kwargs):
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        if self._print_help(args, **kwargs):
            return

        execution = self.run(args, **kwargs)
        if args.async:
            self.print_output('To get the results, execute:\n st2 execution get %s' %
                              (execution.id), six.text_type)
        else:
            self._print_execution_details(execution=execution, args=args, **kwargs)

        if execution.status == 'failed':
            # Exit with non zero if the action has failed
            sys.exit(1)

    def _add_common_options(self):
        root_arg_grp = self.parser.add_mutually_exclusive_group()

        # Display options
        task_list_arg_grp = root_arg_grp.add_argument_group()
        task_list_arg_grp.add_argument('--raw', action='store_true',
                                       help='Raw output, don\'t shot sub-tasks for workflows.')
        task_list_arg_grp.add_argument('--show-tasks', action='store_true',
                                       help='Whether to show sub-tasks of an execution.')
        task_list_arg_grp.add_argument('--depth', type=int, default=-1,
                                       help='Depth to which to show sub-tasks. \
                                             By default all are shown.')
        task_list_arg_grp.add_argument('-w', '--width', nargs='+', type=int, default=None,
                                       help='Set the width of columns in output.')

        execution_details_arg_grp = root_arg_grp.add_mutually_exclusive_group()

        detail_arg_grp = execution_details_arg_grp.add_mutually_exclusive_group()
        detail_arg_grp.add_argument('--attr', nargs='+',
                                    default=['id', 'status', 'parameters', 'result'],
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

        show_tasks = getattr(args, 'show_tasks', False)
        raw = getattr(args, 'raw', False)
        detail = getattr(args, 'detail', False)
        key = getattr(args, 'key', None)
        attr = getattr(args, 'attr', [])

        if show_tasks and not is_workflow_action:
            raise ValueError('--show-tasks option can only be used with workflow actions')

        if not raw and not detail and (show_tasks or is_workflow_action):
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

        instance = execution
        options = {'attributes': ['id', 'action.ref', 'parameters', 'status', 'start_timestamp',
                                  'end_timestamp']}
        options['json'] = args.json
        options['attribute_transform_functions'] = self.attribute_transform_functions
        formatter = execution_formatter.ExecutionResult

        kwargs['depth'] = args.depth
        child_instances = action_exec_mgr.get_property(execution.id, 'children', **kwargs)
        child_instances = self._format_child_instances(child_instances, execution.id)
        child_instances = format_execution_statuses(child_instances)

        if not child_instances:
            # No child error, there might be a global error, include result in the output
            options['attributes'].append('result')

        # On failure we also want to include error message and traceback at the top level
        if instance.status == 'failed':
            status_index = options['attributes'].index('status')
            if isinstance(instance.result, dict):
                tasks = instance.result.get('tasks', [])
            else:
                tasks = []

            top_level_error, top_level_traceback = self._get_top_level_error(live_action=instance)

            if len(tasks) >= 1:
                task_error, task_traceback = self._get_task_error(task=tasks[-1])
            else:
                task_error, task_traceback = None, None

            if top_level_error:
                # Top-level error
                instance.error = top_level_error
                instance.traceback = top_level_traceback
                instance.result = 'See error and traceback.'
                options['attributes'].insert(status_index + 1, 'error')
                options['attributes'].insert(status_index + 2, 'traceback')
            elif task_error:
                # Task error
                instance.error = task_error
                instance.traceback = task_traceback
                instance.result = 'See error and traceback.'
                instance.failed_on = tasks[-1].get('name', 'unknown')
                options['attributes'].insert(status_index + 1, 'error')
                options['attributes'].insert(status_index + 2, 'traceback')
                options['attributes'].insert(status_index + 3, 'failed_on')

        # print root task
        self.print_output(instance, formatter, **options)

        # print child tasks
        if child_instances:
            self.print_output(child_instances, table.MultiColumnTable,
                              attributes=['id', 'status', 'task', 'action', 'start_timestamp'],
                              widths=args.width, json=args.json,
                              yaml=args.yaml,
                              attribute_transform_functions=self.attribute_transform_functions)

    def _get_execution_result(self, execution, action_exec_mgr, args, **kwargs):
        pending_statuses = [
            LIVEACTION_STATUS_REQUESTED,
            LIVEACTION_STATUS_SCHEDULED,
            LIVEACTION_STATUS_RUNNING,
            LIVEACTION_STATUS_CANCELING
        ]

        if not args.async:
            while execution.status in pending_statuses:
                time.sleep(self.poll_interval)
                if not args.json and not args.yaml:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            sys.stdout.write('\n')

            if execution.status == LIVEACTION_STATUS_CANCELED:
                return execution

        return execution

    def _get_top_level_error(self, live_action):
        """
        Retrieve a top level workflow error.

        :return: (error, traceback)
        """
        if isinstance(live_action.result, dict):
            error = live_action.result.get('error', None)
            traceback = live_action.result.get('traceback', None)
        else:
            error = "See result"
            traceback = "See result"

        return error, traceback

    def _get_task_error(self, task):
        """
        Retrieve error message from the provided task.

        :return: (error, traceback)
        """
        if not task:
            return None, None

        result = task['result']

        if isinstance(result, dict):
            stderr = result.get('stderr', None)
            error = result.get('error', None)
            traceback = result.get('traceback', None)
            error = error if error else stderr
        else:
            stderr = None
            error = None
            traceback = None

        return error, traceback

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

        def transform_array(value):
            # Sometimes an array parameter only has a single element:
            #
            #     i.e. "st2 run foopack.fooaction arrayparam=51"
            #
            # Normally, json.loads would throw an exception, and the split method
            # would be used. However, since this is an int, not only would
            # splitting not work, but json.loads actually treats this as valid JSON,
            # but as an int, not an array. This causes a mismatch when the API is called.
            #
            # We want to try to handle this first, so it doesn't get accidentally
            # sent to the API as an int, instead of an array of single-element int.
            try:
                # Force this to be a list containing the single int, then
                # cast the whole thing to string so json.loads can handle it
                value = str([int(value)])
            except ValueError:
                # Original value wasn't an int, so just let it continue
                pass

            # At this point, the input is either a a "json.loads"-able construct
            # like [1, 2, 3], or even [1], or it is a comma-separated list,
            # Try both, in that order.
            try:
                result = json.loads(value)
            except ValueError:
                result = [v.strip() for v in value.split(',')]
            return result

        transformer = {
            'array': transform_array,
            'boolean': (lambda x: ast.literal_eval(x.capitalize())),
            'integer': int,
            'number': float,
            'object': transform_object,
            'string': str
        }

        def normalize(name, value):
            """ The desired type is contained in the action meta-data, so we can look that up
                and call the desired "caster" function listed in the "transformer" dict
            """

            # Users can also specify type for each array parameter inside an action metadata
            # (items: type: int for example) and this information is available here so we could
            # also leverage that to cast each array item to the correct type.

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

        if not args.parameters:
            return result

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
                    if not action:
                        raise resource.ResourceNotFoundError('Action %s not found', args.ref_or_id)
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
                    print(('Action "%s" is not found. ' % args.ref_or_id) +
                          'Do "st2 action list" to see list of available actions.')
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
            'start_timestamp': task.start_timestamp,
            'end_timestamp': getattr(task, 'end_timestamp', None)
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
            self.parser.add_argument('--trace-tag', '--trace_tag',
                                     help='A trace tag string to track execution later.',
                                     dest='trace_tag', required=False)
            self.parser.add_argument('--trace-id',
                                     help='Existing trace id for this execution.',
                                     dest='trace_id', required=False)
            self.parser.add_argument('-a', '--async',
                                     action='store_true', dest='async',
                                     help='Do not wait for action to finish.')
            self.parser.add_argument('-e', '--inherit-env',
                                     action='store_true', dest='inherit_env',
                                     help='Pass all the environment variables '
                                          'which are accessible to the CLI as "env" '
                                          'parameter to the action. Note: Only works '
                                          'with python, local and remote runners.')
            self.parser.add_argument('-u', '--user', type=str, default=None,
                                           help='User under which to run the action (admins only).')

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
        execution.user = args.user

        if not args.trace_id and args.trace_tag:
            execution.context = {'trace_context': {'trace_tag': args.trace_tag}}

        if args.trace_id:
            execution.context = {'trace_context': {'id_': args.trace_id}}

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
        self.commands['cancel'] = ActionExecutionCancelCommand(self.resource, self.app,
                                                               self.subparsers, add_help=False)


POSSIBLE_ACTION_STATUS_VALUES = ('succeeded', 'running', 'scheduled', 'failed', 'canceled')


class ActionExecutionReadCommand(resource.ResourceCommand):
    """
    Base class for read / view commands (list and get).
    """

    @classmethod
    def _get_exclude_attributes(cls, args):
        """
        Retrieve a list of exclude attributes for particular command line arguments.
        """
        exclude_attributes = []

        result_included = False
        trigger_instance_included = False

        for attr in args.attr:
            # Note: We perform startswith check so we correctly detected child attribute properties
            # (e.g. result, result.stdout, result.stderr, etc.)
            if attr.startswith('result'):
                result_included = True

            if attr.startswith('trigger_instance'):
                trigger_instance_included = True

        if not result_included:
            exclude_attributes.append('result')
        if not trigger_instance_included:
            exclude_attributes.append('trigger_instance')

        return exclude_attributes


class ActionExecutionListCommand(ActionExecutionReadCommand):
    display_attributes = ['id', 'action.ref', 'context.user', 'status', 'start_timestamp',
                          'end_timestamp']
    attribute_transform_functions = {
        'start_timestamp': format_isodate_for_user_timezone,
        'end_timestamp': format_isodate_for_user_timezone,
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
                                 help=('List N most recent %s.' %
                                       resource.get_plural_display_name().lower()))
        self.parser.add_argument('-s', '--sort', type=str, dest='sort_order',
                                 default='descending',
                                 help=('Sort %s by start timestamp, '
                                       'asc|ascending (earliest first) '
                                       'or desc|descending (latest first)' %
                                       resource.get_plural_display_name().lower()))

        # Filter options
        self.group.add_argument('--action', help='Action reference to filter the list.')
        self.group.add_argument('--status', help=('Only return executions with the provided status.'
                                                  ' Possible values are \'%s\', \'%s\', \'%s\','
                                                  '\'%s\' or \'%s\''
                                                  '.' % POSSIBLE_ACTION_STATUS_VALUES))
        self.group.add_argument('--trigger_instance',
                                help='Trigger instance id to filter the list.')
        self.parser.add_argument('-tg', '--timestamp-gt', type=str, dest='timestamp_gt',
                                 default=None,
                                 help=('Only return executions with timestamp '
                                       'greater than the one provided. '
                                       'Use time in the format "2000-01-01T12:00:00.000Z".'))
        self.parser.add_argument('-tl', '--timestamp-lt', type=str, dest='timestamp_lt',
                                 default=None,
                                 help=('Only return executions with timestamp '
                                       'lower than the one provided. '
                                       'Use time in the format "2000-01-01T12:00:00.000Z".'))
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
        if args.trigger_instance:
            kwargs['trigger_instance'] = args.trigger_instance
        if not args.showall:
            # null is the magic string that translates to does not exist.
            kwargs['parent'] = 'null'
        if args.timestamp_gt:
            kwargs['timestamp_gt'] = args.timestamp_gt
        if args.timestamp_lt:
            kwargs['timestamp_lt'] = args.timestamp_lt
        if args.sort_order:
            if args.sort_order in ['asc', 'ascending']:
                kwargs['sort_asc'] = True
            elif args.sort_order in ['desc', 'descending']:
                kwargs['sort_desc'] = True

        # We exclude "result" and "trigger_instance" attributes which can contain a lot of data
        # since they are not displayed nor used which speeds the common operation substantially.
        exclude_attributes = self._get_exclude_attributes(args=args)
        exclude_attributes = ','.join(exclude_attributes)
        kwargs['exclude_attributes'] = exclude_attributes

        return self.manager.query(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances = format_wf_instances(self.run(args, **kwargs))

        if not args.json and not args.yaml:
            # Include elapsed time for running executions
            instances = format_execution_statuses(instances)

        self.print_output(reversed(instances), table.MultiColumnTable,
                          attributes=args.attr, widths=args.width,
                          json=args.json,
                          yaml=args.yaml,
                          attribute_transform_functions=self.attribute_transform_functions)


class ActionExecutionGetCommand(ActionRunCommandMixin, ActionExecutionReadCommand):
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
        # We exclude "result" and / or "trigger_instance" attribute if it's not explicitly
        # requested by user either via "--attr" flag or by default.
        exclude_attributes = self._get_exclude_attributes(args=args)
        exclude_attributes = ','.join(exclude_attributes)

        kwargs['params'] = {'exclude_attributes': exclude_attributes}

        execution = self.get_resource_by_id(id=args.id, **kwargs)
        return execution

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        try:
            execution = self.run(args, **kwargs)

            if not args.json and not args.yaml:
                # Include elapsed time for running executions
                execution = format_execution_status(execution)
        except resource.ResourceNotFoundError:
            self.print_not_found(args.id)
            raise OperationFailureException('Execution %s not found.' % (args.id))
        return self._print_execution_details(execution=execution, args=args, **kwargs)


class ActionExecutionCancelCommand(resource.ResourceCommand):

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionCancelCommand, self).__init__(
            resource, 'cancel', 'Cancel %s.' %
            resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('ids',
                                 nargs='+',
                                 help=('IDs of the %ss to cancel.' %
                                       resource.get_display_name().lower()))

    def run(self, args, **kwargs):
        responses = []
        for execution_id in args.ids:
            response = self.manager.delete_by_id(execution_id)
            responses.append([execution_id, response])

        return responses

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        responses = self.run(args, **kwargs)

        for execution_id, response in responses:
            self._print_result(execution_id=execution_id, response=response)

    def _print_result(self, execution_id, response):
        if response and 'faultstring' in response:
            message = response.get('faultstring', 'Cancellation requested for %s with id %s.' %
                                   (self.resource.get_display_name().lower(), execution_id))

        elif response:
            message = '%s with id %s canceled.' % (self.resource.get_display_name().lower(),
                                                   execution_id)
        else:
            message = 'Cannot cancel %s with id %s.' % (self.resource.get_display_name().lower(),
                                                        execution_id)
        print(message)


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
        self.parser.add_argument('--tasks', nargs='*',
                                 help='Name of the workflow tasks to re-run.')
        self.parser.add_argument('--no-reset', dest='no_reset', nargs='*',
                                 help='Name of the with-items tasks to not reset. This only '
                                      'applies to Mistral workflows. By default, all iterations '
                                      'for with-items tasks is rerun. If no reset, only failed '
                                      ' iterations are rerun.')
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

        action_ref = existing_execution.action['ref']
        action = action_mgr.get_by_ref_or_id(action_ref)
        runner = runner_mgr.get_by_name(action.runner_type)

        action_parameters = self._get_action_parameters_from_args(action=action, runner=runner,
                                                                  args=args)

        execution = action_exec_mgr.re_run(execution_id=args.id,
                                           parameters=action_parameters,
                                           tasks=args.tasks,
                                           no_reset=args.no_reset,
                                           **kwargs)

        execution = self._get_execution_result(execution=execution,
                                               action_exec_mgr=action_exec_mgr,
                                               args=args, **kwargs)

        return execution
