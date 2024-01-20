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

from st2client.models import core
from st2client.models.action import Execution
from st2client.models.action_alias import ActionAlias
from st2client.models.action_alias import ActionAliasMatch
from st2client.commands import resource
from st2client.commands.action import ActionRunCommandMixin
from st2client.formatters import table


__all__ = ["ActionAliasBranch", "ActionAliasMatchCommand", "ActionAliasExecuteCommand"]


class ActionAliasBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(ActionAliasBranch, self).__init__(
            ActionAlias,
            description,
            app,
            subparsers,
            parent_parser=parent_parser,
            read_only=False,
            commands={"list": ActionAliasListCommand, "get": ActionAliasGetCommand},
        )

        self.commands["match"] = ActionAliasMatchCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )
        self.commands["execute"] = ActionAliasExecuteCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )
        self.commands["test"] = ActionAliasTestCommand(
            self.resource, self.app, self.subparsers, add_help=True
        )


class ActionAliasListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ["ref", "pack", "description", "enabled"]


class ActionAliasGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ["all"]
    attribute_display_order = [
        "id",
        "ref",
        "pack",
        "name",
        "description",
        "enabled",
        "action_ref",
        "formats",
    ]


class ActionAliasMatchCommand(resource.ResourceCommand):
    display_attributes = ["name", "description"]

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasMatchCommand, self).__init__(
            resource,
            "match",
            "Get the %s that match the command text."
            % resource.get_display_name().lower(),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "match_text",
            metavar="command",
            help=(
                "Get the %s that match the command text."
                % resource.get_display_name().lower()
            ),
        )
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

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        alias_match = ActionAliasMatch()
        alias_match.command = args.match_text

        match, _ = self.manager.match(alias_match, **kwargs)
        return [match]

    def run_and_print(self, args, **kwargs):
        instances = self.run(args, **kwargs)
        self.print_output(
            instances,
            table.MultiColumnTable,
            attributes=args.attr,
            widths=args.width,
            json=args.json,
            yaml=args.yaml,
        )


class ActionAliasExecuteCommand(resource.ResourceCommand):
    display_attributes = ["name"]

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasExecuteCommand, self).__init__(
            resource,
            "execute",
            (
                "Execute the command text by finding a matching %s."
                % resource.get_display_name().lower()
            ),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "command_text",
            metavar="command",
            help=(
                "Execute the command text by finding a matching %s."
                % resource.get_display_name().lower()
            ),
        )
        self.parser.add_argument(
            "-u",
            "--user",
            type=str,
            default=None,
            help="User under which to run the action (admins only).",
        )

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        payload = core.Resource()
        payload.command = args.command_text
        payload.user = args.user or ""
        payload.source_channel = "cli"

        alias_execution_mgr = self.app.client.managers["ActionAliasExecution"]
        execution = alias_execution_mgr.match_and_execute(payload)
        return execution

    def run_and_print(self, args, **kwargs):
        execution = self.run(args, **kwargs)
        print("Matching Action-alias: '%s'" % execution.actionalias["ref"])
        print(
            "To get the results, execute:\n st2 execution get %s"
            % (execution.execution["id"])
        )


class ActionAliasTestCommand(ActionRunCommandMixin, resource.ResourceCommand):
    display_attributes = ["name"]

    def __init__(self, resource, *args, **kwargs):
        super(ActionAliasTestCommand, self).__init__(
            resource,
            "test",
            (
                "Execute the command text by finding a matching %s and format the result."
                % resource.get_display_name().lower()
            ),
            *args,
            **kwargs,
        )

        self.parser.add_argument(
            "command_text",
            metavar="command",
            help=(
                "Execute the command text by finding a matching %s."
                % resource.get_display_name().lower()
            ),
        )
        self.parser.add_argument(
            "-u",
            "--user",
            type=str,
            default=None,
            help="User under which to run the action (admins only).",
        )

        self._add_common_options()
        self.parser.add_argument(
            "-a",
            "--async",
            action="store_true",
            dest="action_async",
            help="Do not wait for action to finish.",
        )

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        payload = core.Resource()
        payload.command = args.command_text
        payload.user = args.user or ""
        payload.source_channel = "cli"

        alias_execution_mgr = self.app.client.managers["ActionAliasExecution"]
        execution = alias_execution_mgr.match_and_execute(payload)
        return execution

    def run_and_print(self, args, **kwargs):
        # 1. Trigger the execution via alias
        print("Triggering execution via action alias")
        print("")

        # NOTE: This will return an error and abort if command matches no aliases so no additional
        # checks are needed
        result = self.run(args, **kwargs)
        execution = Execution.deserialize(result.execution)

        # 2. Wait for it to complete
        print(
            "Execution (%s) has been started, waiting for it to finish..."
            % (execution.id)
        )
        print("")

        action_exec_mgr = self.app.client.managers["Execution"]
        execution = self._get_execution_result(
            execution=execution, action_exec_mgr=action_exec_mgr, args=args, **kwargs
        )
        execution_id = execution.id

        # 3. Run chatops.format_result action with the result of the completed execution
        print("")
        print(f"Execution ({execution_id}) has finished, rendering result...")
        print("")

        format_execution = Execution()
        format_execution.action = "chatops.format_execution_result"
        format_execution.parameters = {"execution_id": execution_id}
        format_execution.user = args.user or ""

        format_execution = action_exec_mgr.create(format_execution, **kwargs)

        print(
            "Execution (%s) has been started, waiting for it to finish..."
            % (format_execution.id)
        )
        print("")

        # 4. Wait for chatops.format_execution_result to finish and print the result
        format_execution = self._get_execution_result(
            execution=format_execution,
            action_exec_mgr=action_exec_mgr,
            args=args,
            force_retry_on_finish=True,
            **kwargs,
        )

        print("")
        print("Formatted ChatOps result message")
        print("")
        print("=" * 80)
        print(format_execution.result["result"]["message"])
        print("=" * 80)
        print("")
