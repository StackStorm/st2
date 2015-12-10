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

from st2client import models
from st2client.commands import resource


class RuleBranch(resource.ResourceBranch):

    def __init__(self, description, app, subparsers, parent_parser=None):
        super(RuleBranch, self).__init__(
            models.Rule, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': RuleListCommand,
                'get': RuleGetCommand,
                'update': RuleUpdateCommand,
                'delete': RuleDeleteCommand
            })

        self.commands['enable'] = RuleEnableCommand(self.resource, self.app, self.subparsers)
        self.commands['disable'] = RuleDisableCommand(self.resource, self.app, self.subparsers)


class RuleListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']


class RuleGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'uid', 'ref', 'pack', 'name', 'description',
                               'enabled']


class RuleUpdateCommand(resource.ContentPackResourceUpdateCommand):
    pass


class RuleEnableCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'description',
                               'enabled']


class RuleDisableCommand(resource.ContentPackResourceDisableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'description',
                               'enabled']


class RuleDeleteCommand(resource.ContentPackResourceDeleteCommand):
    pass
