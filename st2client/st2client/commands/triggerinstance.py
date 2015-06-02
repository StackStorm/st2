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

from st2client.commands import resource
from st2client.commands.noop import NoopCommand
from st2client.models import TriggerInstance


class TriggerInstanceBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(TriggerInstanceBranch, self).__init__(
            TriggerInstance, description, app, subparsers,
            parent_parser=parent_parser,
            commands={
                'list': TriggerInstanceListCommand,
                'get': TriggerInstanceGetCommand,
                'delete': NoopCommand,
                'create': NoopCommand,
                'update': NoopCommand
            })


class TriggerInstanceListCommand(resource.ResourceListCommand):
    display_attributes = ['id', 'trigger', 'occurrence_time', 'payload']


class TriggerInstanceGetCommand(resource.ResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'trigger', 'occurrence_time', 'payload']

    pk_argument_name = 'id'

    @resource.add_auth_token_to_kwargs_from_cli
    def run(self, args, **kwargs):
        resource_id = getattr(args, self.pk_argument_name, None)
        return self.get_resource_by_id(resource_id, **kwargs)
