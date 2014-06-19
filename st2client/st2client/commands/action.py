# -*- coding: utf-8 -*-
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging

from st2client.commands import resource
from st2client.models import action


LOG = logging.getLogger(__name__)


class ActionBranch(resource.ResourceBranch):

    def __init__(self, manager, description,
                 subparsers, parent_parser=None):
        super(ActionBranch, self).__init__(
            action.Action, manager, description, subparsers,
            parent_parser=parent_parser)
        self.commands['execute'] = ActionExecuteCommand(
            self.resource, self.manager, self.subparsers)


class ActionExecuteCommand(resource.ResourceCommand):

    def __init__(self, resource, manager, subparsers):
        super(ActionExecuteCommand, self).__init__(
            'execute', 'Execute an action manually.',
            resource, manager, subparsers)
        self.parser.add_argument('name',
                                 help='Name of the action.')
        self.parser.add_argument('-j', '--json', action='store_true', dest='json',
                                 help='Prints output in JSON format.')

    def run(self, args):
        raise NotImplementedError
