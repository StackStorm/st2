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

from cookiecutter.main import cookiecutter

from st2client import commands


class CreateBranch(commands.Branch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(CreateBranch, self).__init__(
            'create', description, app, subparsers,
            parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help=('List of types of content to create.'))

        self.commands['pack'] = CreatePackCommand(self.app, self.subparsers)
        self.commands['action'] = CreateActionBranch(self.app, self.subparsers)
        self.commands['alias'] = CreateAliasCommand(self.app, self.subparsers)


class CreatePackCommand(commands.Command):
    template = 'https://github.com/enykeev/cookiecutter-st2pack.git'

    def __init__(self, *args, **kwargs):
        super(CreatePackCommand, self).__init__('pack',
                                                'Generate a pack boilerplate.',
                                                *args, **kwargs)

        self.parser.add_argument('directory',
                                 help='Name of the pack directory to create.')

    def run(self, args, **kwargs):
        path, name = os.path.split(args.directory)

        ctx = {}

        if name:
            ctx["Pack Name"] = name

        return cookiecutter(self.template, extra_context=ctx, output_dir=path)

    def run_and_print(self, args, **kwargs):
        return self.run(args, **kwargs)


class CreateActionBranch(commands.Branch):
    def __init__(self, app, subparsers, parent_parser=None):
        super(CreateActionBranch, self).__init__(
            'action', 'Generate an action of specific type.', app, subparsers,
            parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help='List of types of actions to create.')

        self.commands['python'] = CreatePythonActionCommand(self.app, self.subparsers)


class CreatePythonActionCommand(commands.Command):
    template = 'https://github.com/enykeev/cookiecutter-st2action-python.git'

    def __init__(self, *args, **kwargs):
        super(CreatePythonActionCommand, self).__init__('python',
                                                        'Generate a python action boilerplate.',
                                                        *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        ctx = {
            "Action Name": args.name
        }

        return cookiecutter(self.template, extra_context=ctx, output_dir=args.cwd,
                            overwrite_if_exists=True)

    def run_and_print(self, args, **kwargs):
        return self.run(args, **kwargs)


class CreateAliasCommand(commands.Command):
    template = 'https://github.com/enykeev/cookiecutter-st2alias.git'

    def __init__(self, *args, **kwargs):
        super(CreateAliasCommand, self).__init__('alias',
                                                 'Generate an alias boilerplate.',
                                                 *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        ctx = {
            "Alias Name": args.name
        }

        return cookiecutter(self.template, extra_context=ctx, output_dir=args.cwd,
                            overwrite_if_exists=True)

    def run_and_print(self, args, **kwargs):
        return self.run(args, **kwargs)
