# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

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

from six.moves import range

from st2client.models.action import Action, Execution
from st2client.commands import resource
from st2client.commands.resource import ResourceNotFoundError
from st2client.commands.resource import ResourceViewCommand
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.formatters import table
from st2client.formatters import execution as execution_formatter
from st2client.utils import jsutil
from st2client.utils.date import format_isodate_for_user_timezone
from st2client.utils.date import parse as parse_isotime
from st2client.utils.color import format_status

LOG = logging.getLogger(__name__)

LIVEACTION_STATUS_REQUESTED = "requested"
LIVEACTION_STATUS_SCHEDULED = "scheduled"
LIVEACTION_STATUS_DELAYED = "delayed"
LIVEACTION_STATUS_RUNNING = "running"
LIVEACTION_STATUS_SUCCEEDED = "succeeded"
LIVEACTION_STATUS_FAILED = "failed"
LIVEACTION_STATUS_TIMED_OUT = "timeout"
LIVEACTION_STATUS_ABANDONED = "abandoned"
LIVEACTION_STATUS_CANCELING = "canceling"
LIVEACTION_STATUS_CANCELED = "canceled"
LIVEACTION_STATUS_PAUSING = "pausing"
LIVEACTION_STATUS_PAUSED = "paused"
LIVEACTION_STATUS_RESUMING = "resuming"

LIVEACTION_COMPLETED_STATES = [
    LIVEACTION_STATUS_SUCCEEDED,
    LIVEACTION_STATUS_FAILED,
    LIVEACTION_STATUS_TIMED_OUT,
    LIVEACTION_STATUS_CANCELED,
    LIVEACTION_STATUS_ABANDONED,
]

# Who parameters should be masked when displaying action execution output
PARAMETERS_TO_MASK = ["password", "private_key"]

# A list of environment variables which are never inherited when using run
# --inherit-env flag
ENV_VARS_BLACKLIST = [
    "pwd",
    "mail",
    "username",
    "user",
    "path",
    "home",
    "ps1",
    "shell",
    "pythonpath",
    "ssh_tty",
    "ssh_connection",
    "lang",
    "ls_colors",
    "logname",
    "oldpwd",
    "term",
    "xdg_session_id",
]

WORKFLOW_RUNNER_TYPES = ["action-chain", "orquesta"]


def format_parameters(value):
    # Mask sensitive parameters
    if not isinstance(value, dict):
        # No parameters, leave it as it is
        return value

    for param_name, _ in value.items():
        if param_name in PARAMETERS_TO_MASK:
            value[param_name] = "********"

    return value


def format_log_items(value):
    if not value:
        return value

    if not isinstance(value, dict):
        # Already formatted or similar
        return value

    result = []
    for item in value:
        if not isinstance(item, dict):
            # We could end up here if user runs newer versions of the client against old st2
            # instance. We simply ignore those errors.
            continue

        item["timestamp"] = format_isodate_for_user_timezone(item["timestamp"])
        result.append(item)

    return result


# String for indenting etc.
WF_PREFIX = "+ "
NON_WF_PREFIX = "  "
INDENT_CHAR = " "


def format_wf_instances(instances):
    """
    Adds identification characters to a workflow and appropriately shifts
    the non-workflow instances. If no workflows are found does nothing.
    """
    # only add extr chars if there are workflows.
    has_wf = False
    for instance in instances:
        if not getattr(instance, "children", None):
            continue
        else:
            has_wf = True
            break
    if not has_wf:
        return instances
    # Prepend wf and non_wf prefixes.
    for instance in instances:
        if getattr(instance, "children", None):
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
    status = getattr(instance, "status", None)
    start_timestamp = getattr(instance, "start_timestamp", None)
    end_timestamp = getattr(instance, "end_timestamp", None)

    if status == LIVEACTION_STATUS_RUNNING and start_timestamp:
        start_timestamp = instance.start_timestamp
        start_timestamp = parse_isotime(start_timestamp)
        start_timestamp = calendar.timegm(start_timestamp.timetuple())
        now = int(time.time())
        elapsed_seconds = now - start_timestamp
        instance.status = "%s (%ss elapsed)" % (instance.status, elapsed_seconds)
    elif status in LIVEACTION_COMPLETED_STATES and start_timestamp and end_timestamp:
        start_timestamp = parse_isotime(start_timestamp)
        start_timestamp = calendar.timegm(start_timestamp.timetuple())
        end_timestamp = parse_isotime(end_timestamp)
        end_timestamp = calendar.timegm(end_timestamp.timetuple())
        elapsed_seconds = end_timestamp - start_timestamp
        instance.status = "%s (%ss elapsed)" % (instance.status, elapsed_seconds)

    return instance


class ActionBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            Action,
            description,
            app,
            subparsers,
            parent_parser=parent_parser,
            commands={
                "list": ActionListCommand,
                "get": ActionGetCommand,
                "update": ActionUpdateCommand,
                "delete": ActionDeleteCommand,
                "clone": ActionCloneCommand,
            },
        )

        # Registers extended commands
        self.commands["enable"] = ActionEnableCommand(
            self.resource, self.app, self.subparsers
        )
        self.commands["disable"] = ActionDisableCommand(
            self.resource, self.app, self.subparsers
        )
        self.commands["execute"] = ActionRunCommand(
            self.resource, self.app, self.subparsers, add_help=False
        )


class ActionListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ["ref", "pack", "description"]


class ActionGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ["all"]
    attribute_display_order = [
        "id",
        "uid",
        "ref",
        "pack",
        "name",
        "description",
        "enabled",
        "entry_point",
        "runner_type",
        "parameters",
    ]


class ActionUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class ActionEnableCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ["all"]
    attribute_display_order = [
        "id",
        "ref",
        "pack",
        "name",
        "description",
        "enabled",
        "entry_point",
        "runner_type",
        "parameters",
    ]


class ActionDisableCommand(resource.ContentPackResourceDisableCommand):
    display_attributes = ["all"]
    attribute_display_order = [
        "id",
        "ref",
        "pack",
        "name",
        "description",
        "enabled",
        "entry_point",
        "runner_type",
        "parameters",
    ]


class ActionDeleteCommand(resource.ContentPackResourceDeleteCommand):
    def __init__(self, resource, *args, **kwargs):
        super(ActionDeleteCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument(
            "-r",
            "--remove-files",
            action="store_true",
            dest="remove_files",
            default=False,
            help="Remove action files from disk.",
        )

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        instance = self.get_resource(resource_id, **kwargs)
        remove_files = args.remove_files
        self.manager.delete_action(instance, remove_files, **kwargs)
        print('Resource with id "%s" has been successfully deleted.' % (resource_id))

    def run_and_print(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name)

        try:
            self.run(args, **kwargs)
        except ResourceNotFoundError:
            self.print_not_found(resource_id)


class ActionCloneCommand(resource.ContentPackResourceCloneCommand):
    source_ref = "source_ref_or_id"
    dest_pack = "dest_pack_name"
    dest_action = "dest_action_name"

    def __init__(self, resource, *args, **kwargs):
        super(ActionCloneCommand, self).__init__(resource, *args, **kwargs)

        args_list = [
            self.source_ref,
            self.dest_pack,
            self.dest_action,
        ]

        for var in args_list:
            metavar = self._get_metavar_for_argument(argument=var)
            helparg = self._get_help_for_argument(resource=resource, argument=var)
            self.parser.add_argument(var, metavar=metavar, help=helparg)

        self.parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            dest="force",
            help="Overwrite action files on disk if destination exists.",
        )

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        source_ref = getattr(args, self.source_ref, None)
        dest_pack = getattr(args, self.dest_pack, None)
        dest_action = getattr(args, self.dest_action, None)
        dest_ref = "%s.%s" % (dest_pack, dest_action)
        self.get_resource_by_ref_or_id(source_ref, **kwargs)

        try:
            dest_instance = self.get_resource(dest_ref, **kwargs)
        except ResourceNotFoundError:
            dest_instance = None

        overwrite = False

        if dest_instance:
            user_input = ""
            if not args.force:
                user_input = input(
                    "The destination action already exists. Do you want to overwrite? (y/n): "
                )
            if args.force or user_input.lower() == "y" or user_input.lower() == "yes":
                overwrite = True
            else:
                print("Action is not cloned.")
                return

        return self.manager.clone(
            source_ref,
            dest_pack,
            dest_action,
            overwrite=overwrite,
            **kwargs,
        )

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            if not instance:
                return
            self.print_output(
                instance,
                table.PropertyValueTable,
                attributes=["all"],
                json=args.json,
                yaml=args.yaml,
            )
        except ResourceNotFoundError:
            source_ref = getattr(args, self.source_ref, None)
            self.print_not_found(source_ref)
        except Exception as e:
            message = six.text_type(e)
            print("ERROR: %s" % (message))


class ActionRunCommandMixin(object):
    """
    Mixin class which contains utility functions related to action execution.
    """

    display_attributes = [
        "id",
        "action.ref",
        "context.user",
        "parameters",
        "status",
        "start_timestamp",
        "end_timestamp",
        "result",
    ]
    attribute_display_order = [
        "id",
        "action.ref",
        "context.user",
        "parameters",
        "status",
        "start_timestamp",
        "end_timestamp",
        "result",
    ]
    attribute_transform_functions = {
        "start_timestamp": format_isodate_for_user_timezone,
        "end_timestamp": format_isodate_for_user_timezone,
        "parameters": format_parameters,
        "status": format_status,
        "log": format_log_items,
    }

    poll_interval = 2  # how often to poll for execution completion when using sync mode

    def get_resource(self, ref_or_id, **kwargs):
        return self.get_resource_by_ref_or_id(ref_or_id=ref_or_id, **kwargs)

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        if self._print_help(args, **kwargs):
            return

        execution = self.run(args, **kwargs)
        if args.action_async:
            self.print_output(
                "To get the results, execute:\n st2 execution get %s" % (execution.id),
                six.text_type,
            )
            self.print_output(
                "\nTo view output in real-time, execute:\n st2 execution "
                "tail %s" % (execution.id),
                six.text_type,
            )
        else:
            self._print_execution_details(execution=execution, args=args, **kwargs)

        if execution.status == "failed":
            # Exit with non zero if the action has failed
            sys.exit(1)

    def _add_common_options(self):
        root_arg_grp = self.parser.add_mutually_exclusive_group()

        # Display options
        task_list_arg_grp = root_arg_grp.add_argument_group()
        task_list_arg_grp.add_argument(
            "--with-schema",
            default=False,
            action="store_true",
            help=("Show schema_ouput suggestion with action."),
        )

        task_list_arg_grp.add_argument(
            "--raw",
            action="store_true",
            help="Raw output, don't show sub-tasks for workflows.",
        )
        task_list_arg_grp.add_argument(
            "--show-tasks",
            action="store_true",
            help="Whether to show sub-tasks of an execution.",
        )
        task_list_arg_grp.add_argument(
            "--depth",
            type=int,
            default=-1,
            help="Depth to which to show sub-tasks. \
                                             By default all are shown.",
        )
        task_list_arg_grp.add_argument(
            "-w",
            "--width",
            nargs="+",
            type=int,
            default=None,
            help="Set the width of columns in output.",
        )

        execution_details_arg_grp = root_arg_grp.add_mutually_exclusive_group()

        detail_arg_grp = execution_details_arg_grp.add_mutually_exclusive_group()
        detail_arg_grp.add_argument(
            "--attr",
            nargs="+",
            default=self.display_attributes,
            help=(
                "List of attributes to include in the "
                'output. "all" or unspecified will '
                "return all attributes."
            ),
        )
        detail_arg_grp.add_argument(
            "-d",
            "--detail",
            action="store_true",
            help="Display full detail of the execution in table format.",
        )

        result_arg_grp = execution_details_arg_grp.add_mutually_exclusive_group()
        result_arg_grp.add_argument(
            "-k",
            "--key",
            help=(
                "If result is type of JSON, then print specific "
                "key-value pair; dot notation for nested JSON is "
                "supported."
            ),
        )
        result_arg_grp.add_argument(
            "--delay",
            type=int,
            default=None,
            help=(
                "How long (in milliseconds) to delay the "
                "execution before scheduling."
            ),
        )

        # Other options
        detail_arg_grp.add_argument(
            "--tail",
            action="store_true",
            help="Automatically start tailing new execution.",
        )

        # Flag to opt-in to functionality introduced in PR #3670. More robust parsing
        # of complex datatypes is planned for 2.6, so this flag will be deprecated soon
        detail_arg_grp.add_argument(
            "--auto-dict",
            action="store_true",
            dest="auto_dict",
            default=False,
            help="Automatically convert list items to "
            "dictionaries when colons are detected. "
            "(NOTE - this parameter and its functionality will be "
            "deprecated in the next release in favor of a more "
            "robust conversion method)",
        )

        return root_arg_grp

    def _print_execution_details(self, execution, args, **kwargs):
        """
        Print the execution detail to stdout.

        This method takes into account if an executed action was workflow or not
        and formats the output accordingly.
        """
        runner_type = execution.action.get("runner_type", "unknown")
        is_workflow_action = runner_type in WORKFLOW_RUNNER_TYPES

        show_tasks = getattr(args, "show_tasks", False)
        raw = getattr(args, "raw", False)
        detail = getattr(args, "detail", False)
        key = getattr(args, "key", None)
        attr = getattr(args, "attr", [])

        if show_tasks and not is_workflow_action:
            raise ValueError(
                "--show-tasks option can only be used with workflow actions"
            )

        if not raw and not detail and (show_tasks or is_workflow_action):
            self._run_and_print_child_task_list(
                execution=execution, args=args, **kwargs
            )
        else:
            instance = execution

            if detail:
                formatter = table.PropertyValueTable
            else:
                formatter = execution_formatter.ExecutionResult

            if detail:
                options = {"attributes": copy.copy(self.display_attributes)}
            elif key:
                options = {"attributes": ["result.%s" % (key)], "key": key}
            else:
                options = {"attributes": attr}

            options["json"] = args.json
            options["yaml"] = args.yaml
            options["with_schema"] = args.with_schema
            options[
                "attribute_transform_functions"
            ] = self.attribute_transform_functions
            self.print_output(instance, formatter, **options)

    def _run_and_print_child_task_list(self, execution, args, **kwargs):
        action_exec_mgr = self.app.client.managers["Execution"]

        instance = execution
        options = {
            "attributes": [
                "id",
                "action.ref",
                "parameters",
                "status",
                "start_timestamp",
                "end_timestamp",
                "log",
            ]
        }
        options["json"] = args.json
        options["attribute_transform_functions"] = self.attribute_transform_functions
        formatter = execution_formatter.ExecutionResult

        kwargs["depth"] = args.depth
        child_instances = action_exec_mgr.get_property(
            execution.id, "children", **kwargs
        )
        child_instances = self._format_child_instances(child_instances, execution.id)
        child_instances = format_execution_statuses(child_instances)

        if not child_instances:
            # No child error, there might be a global error, include result in the output
            options["attributes"].append("result")

        status_index = options["attributes"].index("status")

        if hasattr(instance, "result") and isinstance(instance.result, dict):
            tasks = instance.result.get("tasks", [])
        else:
            tasks = []

        # On failure we also want to include error message and traceback at the top level
        if instance.status == "failed":
            top_level_error, top_level_traceback = self._get_top_level_error(
                live_action=instance
            )

            if len(tasks) >= 1:
                task_error, task_traceback = self._get_task_error(task=tasks[-1])
            else:
                task_error, task_traceback = None, None

            if top_level_error:
                # Top-level error
                instance.error = top_level_error
                instance.traceback = top_level_traceback
                instance.result = "See error and traceback."
                options["attributes"].insert(status_index + 1, "error")
                options["attributes"].insert(status_index + 2, "traceback")
            elif task_error:
                # Task error
                instance.error = task_error
                instance.traceback = task_traceback
                instance.result = "See error and traceback."
                instance.failed_on = tasks[-1].get("name", "unknown")
                options["attributes"].insert(status_index + 1, "error")
                options["attributes"].insert(status_index + 2, "traceback")
                options["attributes"].insert(status_index + 3, "failed_on")

        # Include result on the top-level object so user doesn't need to issue another command to
        # see the result
        if len(tasks) >= 1:
            task_result = self._get_task_result(task=tasks[-1])

            if task_result:
                instance.result_task = tasks[-1].get("name", "unknown")
                options["attributes"].insert(status_index + 1, "result_task")
                options["attributes"].insert(status_index + 2, "result")
                instance.result = task_result
        # Otherwise include the result of the workflow execution.
        else:
            if "result" not in options["attributes"]:
                options["attributes"].append("result")

        # print root task
        self.print_output(instance, formatter, **options)

        # print child tasks
        if child_instances:
            self.print_output(
                child_instances,
                table.MultiColumnTable,
                attributes=["id", "status", "task", "action", "start_timestamp"],
                widths=args.width,
                json=args.json,
                yaml=args.yaml,
                attribute_transform_functions=self.attribute_transform_functions,
            )

    def _get_execution_result(
        self, execution, action_exec_mgr, args, force_retry_on_finish=False, **kwargs
    ):
        """
        :param force_retry_on_finish: True to retry execution details on finish even if the
                                      execution which is passed to this method has already finished.
                                      This ensures we have latest state available for that
                                      execution.
        """
        pending_statuses = [
            LIVEACTION_STATUS_REQUESTED,
            LIVEACTION_STATUS_SCHEDULED,
            LIVEACTION_STATUS_RUNNING,
            LIVEACTION_STATUS_CANCELING,
        ]

        if args.tail:
            # Start tailing new execution
            print('Tailing execution "%s"' % (str(execution.id)))
            execution_manager = self.app.client.managers["Execution"]
            stream_manager = self.app.client.managers["Stream"]
            ActionExecutionTailCommand.tail_execution(
                execution=execution,
                execution_manager=execution_manager,
                stream_manager=stream_manager,
                **kwargs,
            )

            execution = action_exec_mgr.get_by_id(execution.id, **kwargs)
            print("")
            return execution

        poll_counter = 0

        if not args.action_async:
            while execution.status in pending_statuses:
                poll_counter += 1
                time.sleep(self.poll_interval)
                if not args.json and not args.yaml:
                    sys.stdout.write(".")
                    sys.stdout.flush()
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            sys.stdout.write("\n")

            if poll_counter == 0 and force_retry_on_finish:
                # In some situations we want to retrieve execution details from API even if it has
                # already finished before performing even a single poll. This ensures we have the
                # latest data for a particular execution.
                execution = action_exec_mgr.get_by_id(execution.id, **kwargs)

            if execution.status == LIVEACTION_STATUS_CANCELED:
                return execution

        return execution

    def _get_top_level_error(self, live_action):
        """
        Retrieve a top level workflow error.

        :return: (error, traceback)
        """
        if isinstance(live_action.result, dict):
            error = live_action.result.get("error", None)
            traceback = live_action.result.get("traceback", None)
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

        result = task["result"]

        if isinstance(result, dict):
            stderr = result.get("stderr", None)
            error = result.get("error", None)
            traceback = result.get("traceback", None)
            error = error if error else stderr
        else:
            stderr = None
            error = None
            traceback = None

        return error, traceback

    def _get_task_result(self, task):
        if not task:
            return None

        return task["result"]

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
            """
            Read file content and return content as string / unicode.

            NOTE: It's only mean to be used to read non-binary files since API right now doesn't
            support passing binary data.
            """
            if not os.path.exists(file_path):
                raise ValueError('File "%s" doesn\'t exist' % (file_path))

            if not os.path.isfile(file_path):
                raise ValueError('"%s" is not a file' % (file_path))

            with open(file_path, "rb") as fp:
                content = fp.read()

            return content.decode("utf-8")

        def transform_object(value):
            # Also support simple key1=val1,key2=val2 syntax
            if value.startswith("{"):
                # Assume it's JSON
                result = value = json.loads(value)
            else:
                pairs = value.split(",")

                result = {}
                for pair in pairs:
                    split = pair.split("=", 1)

                    if len(split) != 2:
                        continue

                    key, value = split
                    result[key] = value
            return result

        def transform_array(value, action_params=None, auto_dict=False):
            action_params = action_params or {}

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
                result = [v.strip() for v in value.split(",")]

            # When each values in this array represent dict type, this converts
            # the 'result' to the dict type value.
            if all([isinstance(x, str) and ":" in x for x in result]) and auto_dict:
                result_dict = {}
                for (k, v) in [x.split(":") for x in result]:
                    # To parse values using the 'transformer' according to the type which is
                    # specified in the action metadata, calling 'normalize' method recursively.
                    if (
                        "properties" in action_params
                        and k in action_params["properties"]
                    ):
                        result_dict[k] = normalize(
                            k, v, action_params["properties"], auto_dict=auto_dict
                        )
                    else:
                        result_dict[k] = v
                return [result_dict]

            return result

        transformer = {
            "array": transform_array,
            "boolean": (lambda x: ast.literal_eval(x.capitalize())),
            "integer": int,
            "number": float,
            "object": transform_object,
            "string": str,
        }

        def get_param_type(key, action_params=None):
            action_params = action_params or action.parameters

            param = None
            if key in runner.runner_parameters:
                param = runner.runner_parameters[key]
            elif key in action_params:
                param = action_params[key]

            if param:
                return param["type"]

            return None

        def normalize(name, value, action_params=None, auto_dict=False):
            """The desired type is contained in the action meta-data, so we can look that up
            and call the desired "caster" function listed in the "transformer" dict
            """
            action_params = action_params or action.parameters

            # By default, this method uses a parameter which is defined in the action metadata.
            # This method assume to be called recursively for parsing values in an array of objects
            # type value according to the nested action metadata definition.
            #
            # This is a best practice to pass a list value as default argument to prevent
            # unforeseen consequence by being created a persistent object.

            # Users can also specify type for each array parameter inside an action metadata
            # (items: type: int for example) and this information is available here so we could
            # also leverage that to cast each array item to the correct type.
            param_type = get_param_type(name, action_params)
            if param_type == "array" and name in action_params:
                return transformer[param_type](
                    value, action_params[name], auto_dict=auto_dict
                )
            elif param_type:
                return transformer[param_type](value)

            return value

        result = {}

        if not args.parameters:
            return result

        for idx in range(len(args.parameters)):
            arg = args.parameters[idx]
            if "=" in arg:
                k, v = arg.split("=", 1)

                # Attribute for files are prefixed with "@"
                if k.startswith("@"):
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

                        if action_ref_or_id == "core.http":
                            # Special case for http runner
                            result["_file_name"] = file_name
                            result["file_content"] = content
                        else:
                            result[k] = content
                    else:
                        # This permits multiple declarations of argument only in the array type.
                        if get_param_type(k) == "array" and k in result:
                            result[k] += normalize(k, v, auto_dict=args.auto_dict)
                        else:
                            result[k] = normalize(k, v, auto_dict=args.auto_dict)

                except Exception as e:
                    # TODO: Move transformers in a separate module and handle
                    # exceptions there
                    if "malformed string" in six.text_type(e):
                        message = (
                            "Invalid value for boolean parameter. "
                            "Valid values are: true, false"
                        )
                        raise ValueError(message)
                    else:
                        raise e
            else:
                result["cmd"] = " ".join(args.parameters[idx:])
                break

        # Special case for http runner
        if "file_content" in result:
            if "method" not in result:
                # Default to POST if a method is not provided
                result["method"] = "POST"

            if "file_name" not in result:
                # File name not provided, use default file name
                result["file_name"] = result["_file_name"]

            del result["_file_name"]

        if args.inherit_env:
            result["env"] = self._get_inherited_env_vars()

        return result

    @add_auth_token_to_kwargs_from_cli
    def _print_help(self, args, **kwargs):
        # Print appropriate help message if the help option is given.
        action_mgr = self.app.client.managers["Action"]
        action_exec_mgr = self.app.client.managers["Execution"]

        if args.help:
            action_ref_or_id = getattr(args, "ref_or_id", None)
            action_exec_id = getattr(args, "id", None)

            if action_exec_id and not action_ref_or_id:
                action_exec = action_exec_mgr.get_by_id(action_exec_id, **kwargs)
                args.ref_or_id = action_exec.action

            if action_ref_or_id:
                try:
                    action = action_mgr.get_by_ref_or_id(args.ref_or_id, **kwargs)
                    if not action:
                        raise resource.ResourceNotFoundError(
                            "Action %s not found" % args.ref_or_id
                        )
                    runner_mgr = self.app.client.managers["RunnerType"]
                    runner = runner_mgr.get_by_name(action.runner_type, **kwargs)
                    parameters, required, optional, _ = self._get_params_types(
                        runner, action
                    )
                    print("")
                    print(textwrap.fill(action.description))
                    print("")
                    if required:
                        required = self._sort_parameters(
                            parameters=parameters, names=required
                        )

                        print("Required Parameters:")
                        [
                            self._print_param(name, parameters.get(name))
                            for name in required
                        ]
                    if optional:
                        optional = self._sort_parameters(
                            parameters=parameters, names=optional
                        )

                        print("Optional Parameters:")
                        [
                            self._print_param(name, parameters.get(name))
                            for name in optional
                        ]
                except resource.ResourceNotFoundError:
                    print(
                        ('Action "%s" is not found. ' % args.ref_or_id)
                        + 'Use "st2 action list" to see the list of available actions.'
                    )
                except Exception as e:
                    print(
                        'ERROR: Unable to print help for action "%s". %s'
                        % (args.ref_or_id, e)
                    )
            else:
                self.parser.print_help()
            return True
        return False

    @staticmethod
    def _print_param(name, schema):
        if not schema:
            raise ValueError('Missing schema for parameter "%s"' % (name))

        wrapper = textwrap.TextWrapper(width=78)
        wrapper.initial_indent = " " * 4
        wrapper.subsequent_indent = wrapper.initial_indent
        print(wrapper.fill(name))
        wrapper.initial_indent = " " * 8
        wrapper.subsequent_indent = wrapper.initial_indent
        if "description" in schema and schema["description"]:
            print(wrapper.fill(schema["description"]))
        if "type" in schema and schema["type"]:
            print(wrapper.fill("Type: %s" % schema["type"]))
        if "enum" in schema and schema["enum"]:
            print(wrapper.fill("Enum: %s" % ", ".join(schema["enum"])))
        if "default" in schema and schema["default"] is not None:
            print(wrapper.fill("Default: %s" % schema["default"]))
        print("")

    @staticmethod
    def _get_params_types(runner, action):
        runner_params = runner.runner_parameters
        action_params = action.parameters
        parameters = copy.copy(runner_params)
        parameters.update(copy.copy(action_params))
        required = set([k for k, v in six.iteritems(parameters) if v.get("required")])

        def is_immutable(runner_param_meta, action_param_meta):
            # If runner sets a param as immutable, action cannot override that.
            if runner_param_meta.get("immutable", False):
                return True
            else:
                return action_param_meta.get("immutable", False)

        immutable = set()
        for param in parameters.keys():
            if is_immutable(runner_params.get(param, {}), action_params.get(param, {})):
                immutable.add(param)

        required = required - immutable
        optional = set(parameters.keys()) - required - immutable

        return parameters, required, optional, immutable

    def _format_child_instances(self, children, parent_id):
        """
        The goal of this method is to add an indent at every level. This way the
        WF is represented as a tree structure while in a list. For the right visuals
        representation the list must be a DF traversal else the idents will end up
        looking strange.
        """
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
                        instance_id = instance.id[
                            instance.id.index(WF_PREFIX) + len(WF_PREFIX) :
                        ]
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
        """
        Formats a task for common representation for action-chain.
        """
        # This really needs to be better handled on the back-end but that would be a bigger
        # change so handling in cli.
        context = getattr(task, "context", None)
        if context and "chain" in context:
            task_name_key = "context.chain.name"
        elif context and "orquesta" in context:
            task_name_key = "context.orquesta.task_name"
        # Use Execution as the object so that the formatter lookup does not change.
        # AKA HACK!
        return Execution(
            **{
                "id": task.id,
                "status": task.status,
                "task": jsutil.get_value(vars(task), task_name_key),
                "action": task.action.get("ref", None),
                "start_timestamp": task.start_timestamp,
                "end_timestamp": getattr(task, "end_timestamp", None),
            }
        )

    def _sort_parameters(self, parameters, names):
        """
        Sort a provided list of action parameters.

        :type parameters: ``list``
        :type names: ``list`` or ``set``
        """
        sorted_parameters = sorted(
            names,
            key=lambda name: self._get_parameter_sort_value(
                parameters=parameters, name=name
            ),
        )

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

        sort_value = parameter.get("position", name)
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
            resource,
            kwargs.pop("name", "execute"),
            "Invoke an action manually.",
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "ref_or_id",
            nargs="?",
            metavar="ref-or-id",
            help="Action reference (pack.action_name) " + "or ID of the action.",
        )
        self.parser.add_argument(
            "parameters",
            nargs="*",
            help="List of keyword args, positional args, "
            "and optional args for the action.",
        )

        self.parser.add_argument(
            "-h",
            "--help",
            action="store_true",
            dest="help",
            help="Print usage for the given action.",
        )

        self._add_common_options()

        if self.name in ["run", "execute"]:
            self.parser.add_argument(
                "--trace-tag",
                "--trace_tag",
                help="A trace tag string to track execution later.",
                dest="trace_tag",
                required=False,
            )
            self.parser.add_argument(
                "--trace-id",
                help="Existing trace id for this execution.",
                dest="trace_id",
                required=False,
            )
            self.parser.add_argument(
                "-a",
                "--async",
                action="store_true",
                dest="action_async",
                help="Do not wait for action to finish.",
            )
            self.parser.add_argument(
                "-e",
                "--inherit-env",
                action="store_true",
                dest="inherit_env",
                help="Pass all the environment variables "
                'which are accessible to the CLI as "env" '
                "parameter to the action. Note: Only works "
                "with python, local and remote runners.",
            )
            self.parser.add_argument(
                "-u",
                "--user",
                type=str,
                default=None,
                help="User under which to run the action (admins only).",
            )

        if self.name == "run":
            self.parser.set_defaults(action_async=False)
        else:
            self.parser.set_defaults(action_async=True)

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if not args.ref_or_id:
            self.parser.error("Missing action reference or id")

        action = self.get_resource(args.ref_or_id, **kwargs)
        if not action:
            raise resource.ResourceNotFoundError(
                'Action "%s" cannot be found.' % (args.ref_or_id)
            )

        runner_mgr = self.app.client.managers["RunnerType"]
        runner = runner_mgr.get_by_name(action.runner_type, **kwargs)
        if not runner:
            raise resource.ResourceNotFoundError(
                'Runner type "%s" for action "%s" cannot be \
                                                 found.'
                % (action.runner_type, action.name)
            )

        action_ref = ".".join([action.pack, action.name])
        action_parameters = self._get_action_parameters_from_args(
            action=action, runner=runner, args=args
        )

        execution = Execution()
        execution.action = action_ref
        execution.parameters = action_parameters
        execution.user = args.user

        if args.delay:
            execution.delay = args.delay

        if not args.trace_id and args.trace_tag:
            execution.context = {"trace_context": {"trace_tag": args.trace_tag}}

        if args.trace_id:
            execution.context = {"trace_context": {"id_": args.trace_id}}

        action_exec_mgr = self.app.client.managers["Execution"]

        execution = action_exec_mgr.create(execution, **kwargs)
        execution = self._get_execution_result(
            execution=execution, action_exec_mgr=action_exec_mgr, args=args, **kwargs
        )

        return execution


class ActionExecutionBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionExecutionBranch, self).__init__(
            Execution,
            description,
            app,
            subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                "list": ActionExecutionListCommand,
                "get": ActionExecutionGetCommand,
            },
        )

        # Register extended commands
        self.commands["re-run"] = ActionExecutionReRunCommand(
            self.resource, self.app, self.subparsers, add_help=False
        )
        self.commands["cancel"] = ActionExecutionCancelCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )
        self.commands["pause"] = ActionExecutionPauseCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )
        self.commands["resume"] = ActionExecutionResumeCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )
        self.commands["tail"] = ActionExecutionTailCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )


POSSIBLE_ACTION_STATUS_VALUES = (
    "succeeded",
    "running",
    "scheduled",
    "paused",
    "failed",
    "canceling",
    "canceled",
)


class ActionExecutionListCommand(ResourceViewCommand):
    display_attributes = [
        "id",
        "action.ref",
        "context.user",
        "status",
        "start_timestamp",
        "end_timestamp",
    ]
    attribute_transform_functions = {
        "start_timestamp": format_isodate_for_user_timezone,
        "end_timestamp": format_isodate_for_user_timezone,
        "parameters": format_parameters,
        "status": format_status,
    }

    def __init__(self, resource, *args, **kwargs):

        self.default_limit = 50

        super(ActionExecutionListCommand, self).__init__(
            resource,
            "list",
            "Get the list of the %s most recent %s."
            % (self.default_limit, resource.get_plural_display_name().lower()),
            *args,
            **kwargs,
        )

        self.resource_name = resource.get_plural_display_name().lower()
        self.group = self.parser.add_argument_group()
        self.parser.add_argument(
            "-n",
            "--last",
            type=int,
            dest="last",
            default=self.default_limit,
            help=(
                "List N most recent %s. Use -n -1 to fetch the full result \
                                       set."
                % self.resource_name
            ),
        )
        self.parser.add_argument(
            "-s",
            "--sort",
            type=str,
            dest="sort_order",
            default="descending",
            help=(
                "Sort %s by start timestamp, "
                "asc|ascending (earliest first) "
                "or desc|descending (latest first)" % self.resource_name
            ),
        )

        # Filter options
        self.group.add_argument("--action", help="Action reference to filter the list.")
        self.group.add_argument(
            "--status",
            help=(
                "Only return executions with the provided \
                                                  status. Possible values are '%s', '%s', \
                                                  '%s', '%s', '%s', '%s' or '%s'"
                "." % POSSIBLE_ACTION_STATUS_VALUES
            ),
        )
        self.group.add_argument(
            "--user", help="Only return executions created by the provided user."
        )
        self.group.add_argument(
            "--trigger_instance", help="Trigger instance id to filter the list."
        )
        self.parser.add_argument(
            "-tg",
            "--timestamp-gt",
            type=str,
            dest="timestamp_gt",
            default=None,
            help=(
                "Only return executions with timestamp "
                "greater than the one provided. "
                'Use time in the format "2000-01-01T12:00:00.000Z".'
            ),
        )
        self.parser.add_argument(
            "-tl",
            "--timestamp-lt",
            type=str,
            dest="timestamp_lt",
            default=None,
            help=(
                "Only return executions with timestamp "
                "lower than the one provided. "
                'Use time in the format "2000-01-01T12:00:00.000Z".'
            ),
        )
        self.parser.add_argument("-l", "--showall", action="store_true", help="")

        # Display options
        self.parser.add_argument(
            "-a",
            "--attr",
            nargs="+",
            default=self.display_attributes,
            help=(
                "List of attributes to include in the "
                'output. "all" will return all '
                "attributes."
            ),
        )
        self.parser.add_argument(
            "-w",
            "--width",
            nargs="+",
            type=int,
            default=None,
            help=("Set the width of columns in output."),
        )

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.action:
            kwargs["action"] = args.action
        if args.status:
            kwargs["status"] = args.status
        if args.user:
            kwargs["user"] = args.user
        if args.trigger_instance:
            kwargs["trigger_instance"] = args.trigger_instance
        if not args.showall:
            # null is the magic string that translates to does not exist.
            kwargs["parent"] = "null"
        if args.timestamp_gt:
            kwargs["timestamp_gt"] = args.timestamp_gt
        if args.timestamp_lt:
            kwargs["timestamp_lt"] = args.timestamp_lt
        if args.sort_order:
            if args.sort_order in ["asc", "ascending"]:
                kwargs["sort_asc"] = True
            elif args.sort_order in ["desc", "descending"]:
                kwargs["sort_desc"] = True

        # We only retrieve attributes which are needed to speed things up
        include_attributes = self._get_include_attributes(args=args)
        if include_attributes:
            kwargs["include_attributes"] = ",".join(include_attributes)

        return self.manager.query_with_count(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):

        result, count = self.run(args, **kwargs)
        instances = format_wf_instances(result)

        if args.json or args.yaml:
            self.print_output(
                reversed(instances),
                table.MultiColumnTable,
                attributes=args.attr,
                widths=args.width,
                json=args.json,
                yaml=args.yaml,
                attribute_transform_functions=self.attribute_transform_functions,
            )

        else:
            # Include elapsed time for running executions
            instances = format_execution_statuses(instances)
            self.print_output(
                reversed(instances),
                table.MultiColumnTable,
                attributes=args.attr,
                widths=args.width,
                attribute_transform_functions=self.attribute_transform_functions,
            )

            if args.last and count and count > args.last:
                table.SingleRowTable.note_box(self.resource_name, args.last)


class ActionExecutionGetCommand(ActionRunCommandMixin, ResourceViewCommand):
    display_attributes = [
        "id",
        "action.ref",
        "context.user",
        "parameters",
        "status",
        "start_timestamp",
        "end_timestamp",
        "log",
        "result",
    ]
    include_attributes = [
        "action.ref",
        "action.runner_type",
        "start_timestamp",
        "end_timestamp",
        "log",
    ]
    pk_argument_name = "id"

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionGetCommand, self).__init__(
            resource,
            "get",
            "Get individual %s." % resource.get_display_name().lower(),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "id",
            nargs="+",
            help=("ID of the %s." % resource.get_display_name().lower()),
        )
        self.parser.add_argument(
            "-x",
            "--exclude-result",
            dest="exclude_result",
            action="store_true",
            default=False,
            help=("Don't retrieve and display the result field"),
        )

        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # We only retrieve attributes which are needed to speed things up
        include_attributes = self._get_include_attributes(
            args=args, extra_attributes=self.include_attributes
        )
        if include_attributes:
            include_attributes = ",".join(include_attributes)
            kwargs["params"] = {"include_attributes": include_attributes}

        if args.exclude_result:
            kwargs["params"] = {"exclude_attributes": "result"}

        resource_ids = getattr(args, self.pk_argument_name, None)
        resources = self._get_multiple_resources(
            resource_ids=resource_ids, kwargs=kwargs
        )
        return resources

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        executions = self.run(args, **kwargs)

        for execution in executions:
            if not args.json and not args.yaml:
                # Include elapsed time for running executions
                execution = format_execution_status(execution)
            self._print_execution_details(execution=execution, args=args, **kwargs)


class ActionExecutionCancelCommand(resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionCancelCommand, self).__init__(
            resource,
            "cancel",
            "Cancel %s." % resource.get_plural_display_name().lower(),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "ids",
            nargs="+",
            help=("IDs of the %ss to cancel." % resource.get_display_name().lower()),
        )

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
        if response and "faultstring" in response:
            message = response.get(
                "faultstring",
                "Cancellation requested for %s with id %s."
                % (self.resource.get_display_name().lower(), execution_id),
            )

        elif response:
            message = "%s with id %s canceled." % (
                self.resource.get_display_name().lower(),
                execution_id,
            )
        else:
            message = "Cannot cancel %s with id %s." % (
                self.resource.get_display_name().lower(),
                execution_id,
            )
        print(message)


class ActionExecutionReRunCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):

        super(ActionExecutionReRunCommand, self).__init__(
            resource,
            kwargs.pop("name", "re-run"),
            "Re-run a particular action.",
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "id", nargs="?", metavar="id", help="ID of action execution to re-run "
        )
        self.parser.add_argument(
            "parameters",
            nargs="*",
            help="List of keyword args, positional args, "
            "and optional args for the action.",
        )
        self.parser.add_argument(
            "--tasks", nargs="*", help="Name of the workflow tasks to re-run."
        )
        self.parser.add_argument(
            "--no-reset",
            dest="no_reset",
            nargs="*",
            help="Name of the with-items tasks to not reset. This only "
            "applies to Orquesta workflows. By default, all iterations "
            "for with-items tasks is rerun. If no reset, only failed "
            " iterations are rerun.",
        )
        self.parser.add_argument(
            "-a",
            "--async",
            action="store_true",
            dest="action_async",
            help="Do not wait for action to finish.",
        )
        self.parser.add_argument(
            "-e",
            "--inherit-env",
            action="store_true",
            dest="inherit_env",
            help="Pass all the environment variables "
            'which are accessible to the CLI as "env" '
            "parameter to the action. Note: Only works "
            "with python, local and remote runners.",
        )
        self.parser.add_argument(
            "-h",
            "--help",
            action="store_true",
            dest="help",
            help="Print usage for the given action.",
        )
        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        existing_execution = self.manager.get_by_id(args.id, **kwargs)

        if not existing_execution:
            raise resource.ResourceNotFoundError(
                'Action execution with id "%s" cannot be found.' % (args.id)
            )

        action_mgr = self.app.client.managers["Action"]
        runner_mgr = self.app.client.managers["RunnerType"]
        action_exec_mgr = self.app.client.managers["Execution"]

        action_ref = existing_execution.action["ref"]
        action = action_mgr.get_by_ref_or_id(action_ref)
        runner = runner_mgr.get_by_name(action.runner_type)

        action_parameters = self._get_action_parameters_from_args(
            action=action, runner=runner, args=args
        )

        execution = action_exec_mgr.re_run(
            execution_id=args.id,
            parameters=action_parameters,
            tasks=args.tasks,
            no_reset=args.no_reset,
            delay=args.delay if args.delay else 0,
            **kwargs,
        )

        execution = self._get_execution_result(
            execution=execution, action_exec_mgr=action_exec_mgr, args=args, **kwargs
        )

        return execution


class ActionExecutionPauseCommand(ActionRunCommandMixin, ResourceViewCommand):
    display_attributes = [
        "id",
        "action.ref",
        "context.user",
        "parameters",
        "status",
        "start_timestamp",
        "end_timestamp",
        "result",
    ]

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionPauseCommand, self).__init__(
            resource,
            "pause",
            "Pause %s (workflow executions only)."
            % resource.get_plural_display_name().lower(),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "ids", nargs="+", help="ID of action execution to pause."
        )

        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        responses = []
        for execution_id in args.ids:
            try:
                response = self.manager.pause(execution_id)
                responses.append([execution_id, response])
            except resource.ResourceNotFoundError:
                self.print_not_found(args.ids)
                raise ResourceNotFoundError(
                    "Execution with id %s not found." % (execution_id)
                )

        return responses

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        responses = self.run(args, **kwargs)

        for execution_id, response in responses:
            self._print_result(args, execution_id, response, **kwargs)

    def _print_result(self, args, execution_id, execution, **kwargs):
        if not args.json and not args.yaml:
            # Include elapsed time for running executions
            execution = format_execution_status(execution)
        return self._print_execution_details(execution=execution, args=args, **kwargs)


class ActionExecutionResumeCommand(ActionRunCommandMixin, ResourceViewCommand):
    display_attributes = [
        "id",
        "action.ref",
        "context.user",
        "parameters",
        "status",
        "start_timestamp",
        "end_timestamp",
        "result",
    ]

    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionResumeCommand, self).__init__(
            resource,
            "resume",
            "Resume %s (workflow executions only)."
            % resource.get_plural_display_name().lower(),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "ids", nargs="+", help="ID of action execution to resume."
        )

        self._add_common_options()

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        responses = []
        for execution_id in args.ids:
            try:
                response = self.manager.resume(execution_id)
                responses.append([execution_id, response])
            except resource.ResourceNotFoundError:
                self.print_not_found(execution_id)
                raise ResourceNotFoundError(
                    "Execution with id %s not found." % (execution_id)
                )

        return responses

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        responses = self.run(args, **kwargs)

        for execution_id, response in responses:
            self._print_result(args, response, **kwargs)

    def _print_result(self, args, execution, **kwargs):
        if not args.json and not args.yaml:
            # Include elapsed time for running executions
            execution = format_execution_status(execution)
        return self._print_execution_details(execution=execution, args=args, **kwargs)


class ActionExecutionTailCommand(resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(ActionExecutionTailCommand, self).__init__(
            resource,
            kwargs.pop("name", "tail"),
            "Tail output of a particular execution.",
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "id",
            nargs="?",
            metavar="id",
            default="last",
            help="ID of action execution to tail.",
        )
        self.parser.add_argument(
            "--type",
            dest="output_type",
            action="store",
            help=("Type of output to tail for. If not provided, " "defaults to all."),
        )
        self.parser.add_argument(
            "--include-metadata",
            dest="include_metadata",
            action="store_true",
            default=False,
            help=("Include metadata (timestamp, output type) with the " "output."),
        )

    def run(self, args, **kwargs):
        pass

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        execution_id = args.id
        output_type = getattr(args, "output_type", None)
        include_metadata = args.include_metadata

        # Special case for id "last"
        if execution_id == "last":
            executions = self.manager.query(limit=1)
            if executions:
                execution = executions[0]
                execution_id = execution.id
            else:
                print("No executions found in db.")
                return
        else:
            execution = self.manager.get_by_id(execution_id, **kwargs)

        if not execution:
            raise ResourceNotFoundError("Execution  with id %s not found." % (args.id))

        execution_manager = self.manager
        stream_manager = self.app.client.managers["Stream"]
        ActionExecutionTailCommand.tail_execution(
            execution=execution,
            execution_manager=execution_manager,
            stream_manager=stream_manager,
            output_type=output_type,
            include_metadata=include_metadata,
            **kwargs,
        )

    @classmethod
    def tail_execution(
        cls,
        execution_manager,
        stream_manager,
        execution,
        output_type=None,
        include_metadata=False,
        **kwargs,
    ):
        execution_id = str(execution.id)

        # Indicates if the execution we are tailing is a child execution in a workflow
        context = cls.get_normalized_context_execution_task_event(execution.__dict__)
        has_parent_attribute = bool(getattr(execution, "parent", None))
        has_parent_execution_id = bool(context["parent_execution_id"])

        is_tailing_execution_child_execution = bool(
            has_parent_attribute or has_parent_execution_id
        )

        # Note: For non-workflow actions child_execution_id always matches parent_execution_id so
        # we don't need to do any other checks to determine if executions represents a workflow
        # action.
        parent_execution_id = execution_id  # noqa

        # Execution has already finished show existing output.
        # NOTE: This doesn't recurse down into child executions if user is tailing a workflow
        # execution
        if execution.status in LIVEACTION_COMPLETED_STATES:
            output = execution_manager.get_output(
                execution_id=execution_id, output_type=output_type
            )
            print(output)
            print(
                "Execution %s has completed (status=%s)."
                % (execution_id, execution.status)
            )
            return

        # We keep track of all the workflow executions which could contain children.
        # For simplicity, we simply keep track of all the execution ids which belong to a
        # particular workflow.
        workflow_execution_ids = set([parent_execution_id])

        # Retrieve parent execution object so we can keep track of any existing children
        # executions (only applies to already running executions).
        filters = {"params": {"include_attributes": "id,children"}}
        execution = execution_manager.get_by_id(id=execution_id, **filters)

        children_execution_ids = getattr(execution, "children", [])
        workflow_execution_ids.update(children_execution_ids)

        events = ["st2.execution__update", "st2.execution.output__create"]
        for event in stream_manager.listen(
            events,
            end_execution_id=execution_id,
            end_event="st2.execution__update",
            **kwargs,
        ):
            status = event.get("status", None)
            is_execution_event = status is not None

            if is_execution_event:
                context = cls.get_normalized_context_execution_task_event(event)
                task_execution_id = context["execution_id"]
                task_name = context["task_name"]
                task_parent_execution_id = context["parent_execution_id"]

                # An execution is considered a child execution if it has parent execution id
                is_child_execution = bool(task_parent_execution_id)

                # Ignore executions which are not part of the execution we are tailing
                if is_child_execution and not is_tailing_execution_child_execution:
                    if task_parent_execution_id not in workflow_execution_ids:
                        continue
                else:
                    if task_execution_id not in workflow_execution_ids:
                        continue

                workflow_execution_ids.add(task_execution_id)

                if is_child_execution:
                    if status == LIVEACTION_STATUS_RUNNING:
                        print(
                            "Child execution (task=%s) %s has started."
                            % (task_name, task_execution_id)
                        )
                        print("")
                        continue
                    elif status in LIVEACTION_COMPLETED_STATES:
                        print("")
                        print(
                            "Child execution (task=%s) %s has finished (status=%s)."
                            % (task_name, task_execution_id, status)
                        )

                        if is_tailing_execution_child_execution:
                            # User is tailing a child execution inside a workflow, stop the command.
                            break
                        else:
                            continue
                    else:
                        # We don't care about other child events so we simply skip then
                        continue
                else:
                    # NOTE: In some situations execution update event with "running" status is
                    # dispatched twice so we ignore any duplicated events
                    if status == LIVEACTION_STATUS_RUNNING and not event.get(
                        "children", []
                    ):
                        print("Execution %s has started." % (execution_id))
                        print("")
                        continue
                    elif status in LIVEACTION_COMPLETED_STATES:
                        # Bail out once parent execution has finished
                        print("")
                        print(
                            "Execution %s has completed (status=%s)."
                            % (execution_id, status)
                        )
                        break
                    else:
                        # We don't care about other execution events
                        continue

            # Ignore events for executions which don't belong to the one we are tailing
            event_execution_id = event["execution_id"]
            if event_execution_id not in workflow_execution_ids:
                continue

            # Filter on output_type if provided
            event_output_type = event.get("output_type", None)
            if (
                output_type != "all"
                and output_type
                and (event_output_type != output_type)
            ):
                continue

            if include_metadata:
                sys.stdout.write(
                    "[%s][%s] %s"
                    % (event["timestamp"], event["output_type"], event["data"])
                )
            else:
                sys.stdout.write(event["data"])

    @classmethod
    def get_normalized_context_execution_task_event(cls, event):
        """
        Return a dictionary with normalized context attributes for execution event or object.
        """
        context = event.get("context", {})

        result = {"parent_execution_id": None, "execution_id": None, "task_name": None}

        if "orquesta" in context:
            result["parent_execution_id"] = context.get("parent", {}).get(
                "execution_id", None
            )
            result["execution_id"] = event["id"]
            result["task_name"] = context.get("orquesta", {}).get(
                "task_name", "unknown"
            )
        else:
            # Action chain workflow
            result["parent_execution_id"] = context.get("parent", {}).get(
                "execution_id", None
            )
            result["execution_id"] = event["id"]
            result["task_name"] = context.get("chain", {}).get("name", "unknown")

        return result
