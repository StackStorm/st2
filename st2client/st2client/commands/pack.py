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

import sys

import editor
import yaml
import argparse

from st2client.models import Config
from st2client.models import Pack
from st2client.models import LiveAction
from st2client.commands import resource
from st2client.commands.action import ActionRunCommandMixin
from st2client.commands.noop import NoopCommand
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
                'get': NoopCommand
            })

        self.commands['register'] = PackRegisterCommand(self.resource, self.app, self.subparsers)
        self.commands['install'] = PackInstallCommand(self.resource, self.app, self.subparsers)
        self.commands['remove'] = PackRemoveCommand(self.resource, self.app, self.subparsers)
        self.commands['search'] = PackSearchCommand(self.resource, self.app, self.subparsers)
        self.commands['show'] = PackShowCommand(self.resource, self.app, self.subparsers)
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
            message = e.message or str(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)


class PackAsyncCommand(ActionRunCommandMixin, resource.ResourceCommand):
    def __init__(self, *args, **kwargs):
        super(PackAsyncCommand, self).__init__(*args, **kwargs)

        self._add_common_options()

    @resource.add_auth_token_to_kwargs_from_cli
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
                execution = LiveAction(**event)

                if execution.id == parent_id \
                        and execution.status in LIVEACTION_COMPLETED_STATES:
                    break

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
            self._print_execution_details(execution=execution, args=args, **kwargs)
            sys.exit(1)


class PackListCommand(resource.ResourceListCommand):
    display_attributes = ['name', 'description', 'version', 'author']
    attribute_display_order = ['name', 'description', 'version', 'author']


class PackShowCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackShowCommand, self).__init__(resource, 'show',
              'Get information about a %s from the index.' % resource.get_display_name().lower(),
              *args, **kwargs)

        self.parser.add_argument('pack',
                                 help='Name of the %s to show.' %
                                 resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.search(args, **kwargs)


class PackInstallCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackInstallCommand, self).__init__(resource, 'install',
            'Install new %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s to install.' %
                                 resource.get_plural_display_name().lower())

        self.parser.formatter_class = argparse.RawDescriptionHelpFormatter
        self.parser.epilog = '''examples:
                        st2 pack install github
                        st2 pack install trello slack
                        st2 pack install stackstorm/st2-mysql
                        st2 pack install https://github.com/StackStorm/st2-kafka.git
        '''

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.install(args.packs, **kwargs)


class PackRemoveCommand(PackAsyncCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRemoveCommand, self).__init__(resource, 'remove',
            'Remove %s.' % resource.get_plural_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('packs',
                                 nargs='+',
                                 metavar='pack',
                                 help='Name of the %s to remove.' %
                                 resource.get_plural_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.remove(args.packs, **kwargs)


class PackRegisterCommand(PackResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackRegisterCommand, self).__init__(resource, 'register',
              'Register a %s: sync all file changes with DB.' % resource.get_display_name().lower(),
              *args, **kwargs)

        self.parser.add_argument('--packs',
                                 nargs='+',
                                 help='Name of the %s(s) to register.' %
                                 resource.get_display_name().lower())

        self.parser.add_argument('--types',
                                 nargs='+',
                                 help='Types of content to register.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.register(args.packs, args.types, **kwargs)


class PackSearchCommand(resource.ResourceTableCommand):
    display_attributes = ['name', 'description', 'version', 'author']
    attribute_display_order = ['name', 'description', 'version', 'author']

    def __init__(self, resource, *args, **kwargs):
        super(PackSearchCommand, self).__init__(resource, 'search',
            'Search for a %s in remote exchange directory.' % resource.get_display_name().lower(),
            *args, **kwargs)

        self.parser.add_argument('query',
                                 help='Search query.')

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        return self.manager.search(args, **kwargs)


class PackConfigCommand(resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):
        super(PackConfigCommand, self).__init__(resource, 'config',
              'Configure a %s based on config schema.' % resource.get_display_name().lower(),
              *args, **kwargs)

        self.parser.add_argument('name',
                                 help='Name of the %s(s) to configure.' %
                                      resource.get_display_name().lower())

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        schema = self.app.client.managers['ConfigSchema'].get_by_ref_or_id(args.name, **kwargs)

        if not schema:
            raise resource.ResourceNotFoundError("%s doesn't have config schema defined" %
                                                 self.resource.get_display_name())

        config = interactive.InteractiveForm(schema.attributes).initiate_dialog()

        message = '---\nDo you want to preview the config in an editor before saving?'
        description = 'Secrets would be shown in plain text.'
        preview_dialog = interactive.Question(message, {'default': 'y', 'description': description})
        if preview_dialog.read() == 'y':
            try:
                contents = yaml.safe_dump(config, indent=4, default_flow_style=False)
                modified = editor.edit(contents=contents)
                config = yaml.safe_load(modified)
            except editor.EditorError as e:
                print(str(e))

        message = '---\nDo you want me to save it?'
        save_dialog = interactive.Question(message, {'default': 'y'})
        if save_dialog.read() == 'n':
            raise OperationFailureException('Interrupted')

        result = self.app.client.managers['Config'].update(Config(pack=args.name, values=config))

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

            message = e.message or str(e)
            print('ERROR: %s' % (message))
            raise OperationFailureException(message)
