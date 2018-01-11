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

from st2client.models import Timer
from st2client.commands import resource


class TimerBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TimerBranch, self).__init__(
            Timer, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': TimerListCommand,
                'get': TimerGetCommand
            })


class TimerListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'uid', 'pack', 'name', 'type', 'parameters']

    def __init__(self, resource, *args, **kwargs):
        super(TimerListCommand, self).__init__(resource, *args, **kwargs)

        self.parser.add_argument('-ty', '--timer-type', type=str, dest='timer_type',
                                 help=("List %s type, example: 'core.st2.IntervalTimer', \
                                       'core.st2.DateTimer', 'core.st2.CronTimer'." %
                                       resource.get_plural_display_name().lower()), required=False)

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        if args.timer_type:
            kwargs['timer_type'] = args.timer_type

        if kwargs:
            return self.manager.query(**kwargs)
        else:
            return self.manager.get_all(**kwargs)


class TimerGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['type', 'pack', 'name', 'description', 'parameters']
