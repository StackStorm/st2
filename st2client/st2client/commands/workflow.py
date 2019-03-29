
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

from __future__ import absolute_import

import logging
import os
import yaml

from st2client import commands
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli


LOG = logging.getLogger(__name__)


class WorkflowBranch(commands.Branch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(WorkflowBranch, self).__init__(
            'workflow', description, app, subparsers,
            parent_parser=parent_parser
        )

        # Add subparser to register subcommands for managing workflows.
        help_message = 'List of commands for managing workflows.'
        self.subparsers = self.parser.add_subparsers(help=help_message)

        # Register workflow commands.
        self.commands['inspect'] = WorkflowInspectionCommand(self.app, self.subparsers)


class WorkflowInspectionCommand(commands.Command):

    def __init__(self, *args, **kwargs):
        name = 'inspect'
        description = 'Inspect workflow definition and return the list of errors if any.'
        args = tuple([name, description] + list(args))
        super(WorkflowInspectionCommand, self).__init__(*args, **kwargs)

        # Add argument options.
        arg_group = self.parser.add_mutually_exclusive_group()

        arg_group.add_argument(
            '--file',
            dest='file',
            help='Local file path to the workflow definition.'
        )

        arg_group.add_argument(
            '--action',
            dest='action',
            help='Reference name for the registered action. This option works only if the file '
                 'referenced by the entry point is installed locally under /opt/stackstorm/packs.'
        )

    @property
    def manager(self):
        return self.app.client.managers['Workflow']

    def get_file_content(self, file_path):
        if not os.path.isfile(file_path):
            raise Exception('File "%s" does not exist on local system.' % file_path)

        with open(file_path, 'r') as f:
            content = f.read()

        return content

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        wf_def_file = args.file

        # If file path not provided, try the action reference. This only works if the command
        # is executed locally where the content is stored.
        if not wf_def_file:
            action_ref = args.action
            action_manager = self.app.client.managers['Action']
            action = action_manager.get_by_ref_or_id(ref_or_id=action_ref)

            if not action:
                raise Exception('Unable to identify action "%s".' % action_ref)

            wf_def_file = '/opt/stackstorm/packs/' + action.pack + '/actions/' + action.entry_point

        wf_def = self.get_file_content(wf_def_file)

        return self.manager.inspect(wf_def, **kwargs)

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        errors = self.run(args, **kwargs)

        if not isinstance(errors, list):
            raise TypeError('The inspection result is not type of list: %s' % errors)

        if not errors:
            print('No errors found in workflow definition.')
            return

        print(yaml.safe_dump(errors, default_flow_style=False, allow_unicode=True))
