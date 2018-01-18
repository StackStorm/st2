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

from st2client.commands import resource
from st2client.formatters import table
from st2client.models import TriggerInstance
from st2client.utils.date import format_isodate_for_user_timezone


class TriggerInstanceResendCommand(resource.ResourceCommand):
    def __init__(self, resource, *args, **kwargs):

        super(TriggerInstanceResendCommand, self).__init__(
            resource, kwargs.pop('name', 're-emit'),
            'Re-emit a particular trigger instance.',
            *args, **kwargs)

        self.parser.add_argument('id', nargs='?',
                                 metavar='id',
                                 help='ID of trigger instance to re-emit.')
        self.parser.add_argument(
            '-h', '--help',
            action='store_true', dest='help',
            help='Print usage for the given command.')

    def run(self, args, **kwargs):
        return self.manager.re_emit(args.id)

    @resource.add_auth_token_to_kwargs_from_cli
    def run_and_print(self, args, **kwargs):
        ret = self.run(args, **kwargs)
        if 'message' in ret:
            print(ret['message'])


class TriggerInstanceBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerInstanceBranch, self).__init__(
            TriggerInstance, description, app, subparsers,
            parent_parser=parent_parser, read_only=True,
            commands={
                'list': TriggerInstanceListCommand,
                'get': TriggerInstanceGetCommand
            })

        self.commands['re-emit'] = TriggerInstanceResendCommand(self.resource, self.app,
                                                                self.subparsers, add_help=False)


class TriggerInstanceListCommand(resource.ResourceCommand):
    display_attributes = ['id', 'trigger', 'occurrence_time', 'status']

    attribute_transform_functions = {
        'occurrence_time': format_isodate_for_user_timezone
    }

    def __init__(self, resource, *args, **kwargs):

        self.default_limit = 50

        super(TriggerInstanceListCommand, self).__init__(
            resource, 'list', 'Get the list of the %s most recent %s.' %
            (self.default_limit, resource.get_plural_display_name().lower()),
            *args, **kwargs)

        self.resource_name = resource.get_plural_display_name().lower()
        self.group = self.parser.add_argument_group()
        self.parser.add_argument('-n', '--last', type=int, dest='last',
                                 default=self.default_limit,
                                 help=('List N most recent %s. Use -n -1 to fetch the full result \
                                       set.' % self.resource_name))

        # Filter options
        self.group.add_argument('--trigger', help='Trigger reference to filter the list.')

        self.parser.add_argument('-tg', '--timestamp-gt', type=str, dest='timestamp_gt',
                                 default=None,
                                 help=('Only return trigger instances with occurrence_time '
                                       'greater than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))
        self.parser.add_argument('-tl', '--timestamp-lt', type=str, dest='timestamp_lt',
                                 default=None,
                                 help=('Only return trigger instances with timestamp '
                                       'lower than the one provided. '
                                       'Use time in the format 2000-01-01T12:00:00.000Z'))

        self.group.add_argument('--status',
                                help='Can be pending, processing, processed or processing_failed.')

        # Display options
        self.parser.add_argument('-a', '--attr', nargs='+',
                                 default=self.display_attributes,
                                 help=('List of attributes to include in the '
                                       'output. "all" will return all '
                                       'attributes.'))
        self.parser.add_argument('-w', '--width', nargs='+', type=int,
                                 default=None,
                                 help=('Set the width of columns in output.'))

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        # Filtering options
        if args.trigger:
            kwargs['trigger'] = args.trigger
        if args.timestamp_gt:
            kwargs['timestamp_gt'] = args.timestamp_gt
        if args.timestamp_lt:
            kwargs['timestamp_lt'] = args.timestamp_lt
        if args.status:
            kwargs['status'] = args.status

        return self.manager.query_with_count(limit=args.last, **kwargs)

    def run_and_print(self, args, **kwargs):
        instances, count = self.run(args, **kwargs)
        if args.json or args.yaml:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              json=args.json, yaml=args.yaml,
                              attribute_transform_functions=self.attribute_transform_functions)
        else:
            self.print_output(reversed(instances), table.MultiColumnTable,
                              attributes=args.attr, widths=args.width,
                              attribute_transform_functions=self.attribute_transform_functions)
            if args.last and count and count > args.last:
                table.SingleRowTable.note_box(self.resource_name, args.last)


class TriggerInstanceGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'trigger', 'occurrence_time', 'payload']

    pk_argument_name = 'id'

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        return self.get_resource_by_id(resource_id, **kwargs)
