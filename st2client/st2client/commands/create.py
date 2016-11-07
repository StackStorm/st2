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

from collections import OrderedDict
import errno
import os
import pkg_resources

import yaml

from st2client import commands
from st2client.exceptions.operations import OperationFailureException
from st2client.utils import interactive
from st2client.utils import jinja

BOILERPLATES_DIRECTORY = '../bolierplates'

env = jinja.get_jinja_environment()


def _load_schema(content_type):
    class OrderedLoader(yaml.Loader):
        pass

    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return OrderedDict(loader.construct_pairs(node))

    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)

    schema_path = '/'.join((BOILERPLATES_DIRECTORY, '%s.schema.yaml' % content_type))
    schema_string = pkg_resources.resource_string(__name__, schema_path)

    return yaml.load(schema_string, OrderedLoader)


class CreateBranch(commands.Branch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(CreateBranch, self).__init__(
            'create', description, app, subparsers,
            parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help='List of types of content to create.')

        self.commands['pack'] = CreatePackCommand(self.app, self.subparsers)
        self.commands['action'] = CreateActionBranch(self.app, self.subparsers)
        self.commands['alias'] = CreateAliasCommand(self.app, self.subparsers)
        self.commands['rule'] = CreateRuleCommand(self.app, self.subparsers)


class CreateCommand(commands.Command):
    type = None

    def __init__(self, *args, **kwargs):
        super(CreateCommand, self).__init__(*args, **kwargs)
        self.schema = _load_schema(self.type)

    def run(self, args, **kwargs):
        context = interactive.ProgressiveInteractiveForm(self.schema).initiate_dialog()

        template_dir_path = '/'.join((BOILERPLATES_DIRECTORY, self.type))
        resources = pkg_resources.resource_listdir(__name__, template_dir_path)
        for resource in resources:
            template_path = '/'.join((template_dir_path, resource))

            if pkg_resources.resource_isdir(__name__, template_path):
                listing = pkg_resources.resource_listdir(__name__, template_path)
                resources.extend(('/'.join((resource, path)) for path in listing))
            else:
                template = pkg_resources.resource_string(__name__, template_path)
                base_path, extension = os.path.splitext(resource)

                if extension == '.j2':
                    content = env.from_string(template).render(context)
                else:
                    base_path = resource
                    content = template

                base_path = env.from_string(base_path).render(context)
                content_path = os.path.join(args.directory, *base_path.split('/'))

                try:
                    os.makedirs(os.path.dirname(content_path))
                except OSError as e:
                    if e.errno != errno.EEXIST:
                        raise

                with open(content_path, 'w') as f:
                    f.write(content)

    def run_and_print(self, args, **kwargs):
        return self.run(args, **kwargs)


class CreatePackCommand(CreateCommand):
    type = 'pack'

    def __init__(self, *args, **kwargs):
        super(CreatePackCommand, self).__init__('pack',
                                                'Generate a pack boilerplate.',
                                                *args, **kwargs)

        self.parser.add_argument('directory',
                                 help='Name of the pack directory to create.')

    def run(self, args, **kwargs):
        if os.path.exists(args.directory):
            if not os.path.isdir(args.directory):
                raise OperationFailureException('Path %s is not a directory. Aborting.' %
                                                os.path.abspath(args.directory))

            message = 'Directory already exists. Do you want to override it?'
            exists_dialog = interactive.Question(message, {'default': 'y'})
            if exists_dialog.read() != 'y':
                raise OperationFailureException('Directory %s already exists. Aborting.' %
                                                os.path.abspath(args.directory))

        path, name = os.path.split(args.directory)

        if name:
            self.schema['name']['default'] = name

        super(CreatePackCommand, self).run(args, **kwargs)


class CreateActionBranch(commands.Branch):
    def __init__(self, app, subparsers, parent_parser=None):
        super(CreateActionBranch, self).__init__(
            'action', 'Generate an action of specific type.', app, subparsers,
            parent_parser=parent_parser)

        # Registers subcommands for managing the resource type.
        self.subparsers = self.parser.add_subparsers(
            help='List of types of actions to create.')

        self.commands['python'] = CreatePythonActionCommand(self.app, self.subparsers)
        self.commands['action-chain'] = CreateActionChainCommand(self.app, self.subparsers)
        self.commands['remote-shell-cmd'] = CreateRemoteShellCmdActionCommand(self.app,
                                                                              self.subparsers)
        self.commands['remote-shell-script'] = CreateRemoteShellScriptActionCommand(self.app,
                                                                                    self.subparsers)


class CreatePythonActionCommand(CreateCommand):
    type = 'action/python'

    def __init__(self, *args, **kwargs):
        super(CreatePythonActionCommand, self).__init__('python',
                                                        'Generate a python action boilerplate.',
                                                        *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreatePythonActionCommand, self).run(args, **kwargs)


class CreateRemoteShellCmdActionCommand(CreateCommand):
    type = 'action/remote-shell-cmd'

    def __init__(self, *args, **kwargs):
        super(CreateRemoteShellCmdActionCommand, self).__init__(
            'remote-shell-cmd',
            'Generate a remote shell cmd action boilerplate.',
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreateRemoteShellCmdActionCommand, self).run(args, **kwargs)


class CreateRemoteShellScriptActionCommand(CreateCommand):
    type = 'action/remote-shell-script'

    def __init__(self, *args, **kwargs):
        super(CreateRemoteShellScriptActionCommand, self).__init__(
            'remote-shell-script',
            'Generate a remote shell script action boilerplate.',
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreateRemoteShellScriptActionCommand, self).run(args, **kwargs)


class CreateActionChainCommand(CreateCommand):
    type = 'action/action-chain'

    def __init__(self, *args, **kwargs):
        super(CreateActionChainCommand, self).__init__(
            'action-chain',
            'Generate a action chain boilerplate.',
            *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the action to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreateActionChainCommand, self).run(args, **kwargs)


class CreateAliasCommand(CreateCommand):
    type = 'alias'

    def __init__(self, *args, **kwargs):
        super(CreateAliasCommand, self).__init__('alias',
                                                 'Generate an alias boilerplate.',
                                                 *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the alias to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreateAliasCommand, self).run(args, **kwargs)


class CreateRuleCommand(CreateCommand):
    type = 'rule'

    def __init__(self, *args, **kwargs):
        super(CreateRuleCommand, self).__init__('rule',
                                                'Generate a rule boilerplate.',
                                                *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the rule to create.')

        self.parser.add_argument('--cwd',
                                 dest='directory',
                                 default='.',
                                 help='Path to the pack directory.')

    def run(self, args, **kwargs):
        self.schema['name']['default'] = args.name

        super(CreateRuleCommand, self).run(args, **kwargs)
