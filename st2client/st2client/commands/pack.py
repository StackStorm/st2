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

import sys

import six
import editor
import yaml

from st2client.models import Config
from st2client.models import Pack
from st2client.models import Execution
from st2client.commands import resource
from st2client.commands.resource import add_auth_token_to_kwargs_from_cli
from st2client.commands.action import ActionRunCommandMixin
from st2client.formatters import table
from st2client.exceptions.operations import OperationFailureException
import st2client.utils.terminal as term
from st2client.utils import interactive


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


class PackBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PackBranch, self).__init__(
            Pack, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': PackListCommand,
                'get': PackGetCommand
            })

        self.commands['show'] = PackShowCommand(self.resource, self.app, self.subparsers)
        self.commands['search'] = PackSearchCommand(self.resource, self.app, self.subparsers)
        self.commands['install'] = PackInstallCommand(self.resource, self.app, self.subparsers)
        self.commands['remove'] = PackRemoveCommand(self.resource, self.app, self.subparsers)
        self.commands['register'] = PackRegisterCommand(self.resource, self.app, self.subparsers)
        self.commands['config'] = PackConfigCommand(self.resource, self.app, self.subparsers)


class PackResourceCommand(resource.ResourceCommand):
    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            if not instance:
                raise resource.ResourceNotFoundError("No matching items found")
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json, yaml=args.yaml)
        except resource.ResourceNotFoundError:
            print("No matching items found")
        except Exception as e:
            message = six.text_type(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)


class PackAsyncCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def __init__(self, *args, **kwargs):
        super(PackAsyncCommand, self).__init__(*args, **kwargs)

        self.parser.add_argument('-w', '--width', nargs='+', type=int, default=None,
                                       help='Set the width of columns in output.')

        detail_arg_grp = self.parser.add_mutually_exclusive_group()
        detail_arg_grp.add_argument('--attr', nargs='+',
                                    default=['name', 'description', 'version', 'author'],
                                    help=('List of attributes to include in the '
                                          'output. "all" or unspecified will '
                                          'return all attributes.'))
        detail_arg_grp.add_argument('-d', '--detail', action='store_true',
                                    help='Display full detail of the execution in table format.')

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        instance = self.run(args, **kwargs)
        if not instance:
            raise Exception('Server did not create instance.')

        parent_id = instance.execution_id

        stream_mgr = self.app.client.managers['Stream']

        execution = None

        with term.TaskIndicator() as indicator:
            events = ['st2.execution__create', 'st2.execution__update']
            for event in stream_mgr.listen(events, **kwargs):
                execution = Execution(**event)

                if execution.id == parent_id \
                        and execution.status in LIVEACTION_COMPLETED_STATES:
                    break

                # Suppress intermediate output in case output formatter is requested
                if args.json or args.yaml:
                    continue

                if getattr(execution, 'parent', None) == parent_id:
                    status = execution.status
                    name = execution.context['chain']['name']

                    if status == LIVEACTION_STATUS_SCHEDULED:
                        indicator.add_stage(status, name)
                    if status == LIVEACTION_STATUS_RUNNING:
                        indicator.update_stage(status, name)
                    if status in LIVEACTION_COMPLETED_STATES:
                        indicator.finish_stage(status, name)

        if execution and execution.status == LIVEACTION_STATUS_FAILED:
            args.depth = 1
            self._print_execution_details(execution=execution, args=args, **kwargs)
            sys.exit(1)

        return self.app.client.managers['Execution'].get_by_id(parent_id, **kwargs)


class PackListCommand(resource.ResourceListCommand):
    display_attributes = ['ref', 'name', 'description', 'version', 'author']
    attribute_display_order = ['ref', 'name', 'description', 'version', 'author']


class PackGetCommand(resource.ResourceGetCommand):
    pk_argument_name = 'ref'
    display_attributes = ['name', 'version', 'author', 'email', 'keywords', 'description']
    attribute_display_order = ['name', 'version', 'author', 'email', 'keywords', 'description']
    help_string = 'Get information about an installed pack.'


class PackShowCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        help_string = ('Get information about an available %s from the index.' %
                       resource.get_display_name().lower())
        super(PackShowCommand, self).__init__(resource, 'show', help_string,
                                              *args, **kwargs)

        self.parser.add_argument('pack',
                                 help='Name of the %s to show.' %
                                 resource.get_display_name().lower())

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.search(args, **kwargs)


class PackInstallCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackInstallCommand, self).__init__(resource, 'install', 'Install new %s.'
                                                 % resource.get_plural_display_name().lower(),
                                                 *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s in Exchange, or a git repo URL.' %
                                 resource.get_plural_display_name().lower())
        self.parser.add_argument('--python3',
                                 action='store_true',
                                 default=False,
                                 help='Use Python 3 binary for pack virtual environment.')
        self.parser.add_argument('--force',
                                 action='store_true',
                                 default=False,
                                 help='Force pack installation.')

    def run(self, args, **kwargs):
        is_structured_output = args.json or args.yaml

        # If structured output is requested, do not print information about contents of pack
        # This information is already exposed via st2 pack show ${pack_name} -j
        if not is_structured_output:
            self._get_content_counts_for_pack(args, **kwargs)

        return self.manager.install(args.packs, python3=args.python3, force=args.force, **kwargs)

    def _get_content_counts_for_pack(self, args, **kwargs):
        # Global content list, excluding "tests"
        # Note: We skip this step for local packs
        pack_content = {'actions': 0, 'rules': 0, 'sensors': 0, 'aliases': 0, 'triggers': 0}

        if len(args.packs) == 1:
            args.pack = args.packs[0]

            if args.pack.startswith('file://'):
                return

            pack_info = self.manager.search(args, ignore_errors=True, **kwargs)
            content = getattr(pack_info, 'content', {})

            if content:
                for entity in content.keys():
                    if entity in pack_content:
                        pack_content[entity] += content[entity]['count']
                self._print_pack_content(args.packs, pack_content)

        else:
            pack_content = pack_content.fromkeys(pack_content, 0)
            # TODO: Better solution is to update endpoint query param for one API call
            #       example: ?packs=pack1,pack2,pack3
            for pack in args.packs:
                # args.pack required for search
                args.pack = pack

                if args.pack.startswith('file://'):
                    return

                pack_info = self.manager.search(args, ignore_errors=True, **kwargs)
                content = getattr(pack_info, 'content', {})

                if content:
                    for entity in content.keys():
                        if entity in pack_content:
                            pack_content[entity] += content[entity]['count']
            if content:
                self._print_pack_content(args.packs, pack_content)

    @staticmethod
    def _print_pack_content(pack_name, pack_content):
        print('\nFor the "%s" %s, the following content will be registered:\n'
              % (', '.join(pack_name), 'pack' if len(pack_name) == 1 else 'packs'))
        for item, count in pack_content.items():
            print('%-10s|  %s' % (item, count))
        print('\nInstallation may take a while for packs with many items.')

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        instance = super(PackInstallCommand, self).run_and_print(args, **kwargs)
        # Hack to get a list of resolved references of installed packs
        packs = instance.result['tasks'][1]['result']['result']

        if len(packs) == 1:
            pack_instance = self.app.client.managers['Pack'].get_by_ref_or_id(packs[0], **kwargs)
            self.print_output(pack_instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json, yaml=args.yaml,
                              attribute_display_order=self.attribute_display_order)
        else:
            all_pack_instances = self.app.client.managers['Pack'].get_all(**kwargs)
            pack_instances = []

            for pack in all_pack_instances:
                if pack.name in packs:
                    pack_instances.append(pack)

            self.print_output(pack_instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml)


class PackRemoveCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRemoveCommand, self).__init__(resource, 'remove', 'Remove %s.'
                                                % resource.get_plural_display_name().lower(),
                                                *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s to remove.' %
                                 resource.get_plural_display_name().lower())

    def run(self, args, **kwargs):
        return self.manager.remove(args.packs, **kwargs)

    @add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        all_pack_instances = self.app.client.managers['Pack'].get_all(**kwargs)

        super(PackRemoveCommand, self).run_and_print(args, **kwargs)

        packs = args.packs

        if len(packs) == 1:
            pack_instance = self.app.client.managers['Pack'].get_by_ref_or_id(packs[0], **kwargs)

            if pack_instance:
                raise OperationFailureException('Pack %s has not been removed properly' % packs[0])

            removed_pack_instance = next((pack for pack in all_pack_instances
                                         if pack.name == packs[0]), None)

            self.print_output(removed_pack_instance, table.PropertyValueTable,
                              attributes=args.attr, json=args.json, yaml=args.yaml,
                              attribute_display_order=self.attribute_display_order)
        else:
            remaining_pack_instances = self.app.client.managers['Pack'].get_all(**kwargs)
            pack_instances = []

            for pack in all_pack_instances:
                if pack.name in packs:
                    pack_instances.append(pack)
                if pack in remaining_pack_instances:
                    raise OperationFailureException('Pack %s has not been removed properly'
                                                    % pack.name)

            self.print_output(pack_instances, table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml)


class PackRegisterCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRegisterCommand, self).__init__(resource, 'register',
                                                  'Register %s(s): sync all file changes with DB.'
                                                  % resource.get_display_name().lower(),
                                                  *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='*',
                                 metavar='pack',
                                 help='Name of the %s(s) to register.' %
                                 resource.get_display_name().lower())

        self.parser.add_argument('--types',
                                 nargs='+',
                                 help='Types of content to register.')

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.register(args.packs, args.types, **kwargs)


class PackSearchCommand(resource.ResourceTableCommand):
    display_attributes = ['name', 'description', 'version', 'author']
    attribute_display_order = ['name', 'description', 'version', 'author']

    def __init__(self, resource, *args, **kwargs):
        super(PackSearchCommand, self).__init__(resource, 'search',
                                                'Search the index for a %s with any attribute \
                                                matching the query.'
                                                % resource.get_display_name().lower(),
                                                *args, **kwargs)

        self.parser.add_argument('query',
                                 help='Search query.')

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.search(args, **kwargs)


class PackConfigCommand(resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackConfigCommand, self).__init__(resource, 'config',
                                                'Configure a %s based on config schema.'
                                                % resource.get_display_name().lower(),
                                                *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the %s(s) to configure.' %
                                      resource.get_display_name().lower())

    @add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        schema = self.app.client.managers['ConfigSchema'].get_by_ref_or_id(args.name, **kwargs)

        if not schema:
            msg = '%s "%s" doesn\'t exist or doesn\'t have a config schema defined.'
            raise resource.ResourceNotFoundError(msg % (self.resource.get_display_name(),
                                                        args.name))

        config = interactive.InteractiveForm(schema.attributes).initiate_dialog()

        message = '---\nDo you want to preview the config in an editor before saving?'
        description = 'Secrets will be shown in plain text.'
        preview_dialog = interactive.Question(message, {'default': 'y',
                                                        'description': description})
        if preview_dialog.read() == 'y':
            try:
                contents = yaml.safe_dump(config, indent=4, default_flow_style=False)
                modified = editor.edit(contents=contents)
                config = yaml.safe_load(modified)
            except editor.EditorError as e:
                print(six.text_type(e))

        message = '---\nDo you want me to save it?'
        save_dialog = interactive.Question(message, {'default': 'y'})
        if save_dialog.read() == 'n':
            raise OperationFailureException('Interrupted')

        config_item = Config(pack=args.name, values=config)
        result = self.app.client.managers['Config'].update(config_item, **kwargs)

        return result

    def run_and_print(self, args, **kwargs):
        try:
            instance = self.run(args, **kwargs)
            if not instance:
                raise Exception("Configuration failed")
            self.print_output(instance, table.PropertyValueTable,
                              attributes=['all'], json=args.json, yaml=args.yaml)
        except (KeyboardInterrupt, SystemExit):
            raise OperationFailureException('Interrupted')
        except Exception as e:
            if self.app.client.debug:
                raise

            message = six.text_type(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)
