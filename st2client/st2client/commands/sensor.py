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

from st2client.models import Sensor
from st2client.commands import resource


class SensorBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(SensorBranch, self).__init__(
            Sensor, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': SensorListCommand,
                'get': SensorGetCommand
            })

        self.commands['enable'] = SensorEnableCommand(self.resource, self.app, self.subparsers)
        self.commands['disable'] = SensorDisableCommand(self.resource, self.app, self.subparsers)


class SensorListCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['ref', 'pack', 'description', 'enabled']


class SensorGetCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'uid', 'ref', 'pack', 'name', 'enabled', 'entry_point',
                               'artifact_uri', 'trigger_types']


class SensorEnableCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'poll_interval',
                               'entry_point', 'artifact_uri', 'trigger_types']


class SensorDisableCommand(resource.ContentPackResourceDisableCommand):
    display_attributes = ['all']
    attribute_display_order = ['id', 'ref', 'pack', 'name', 'enabled', 'poll_interval',
                               'entry_point', 'artifact_uri', 'trigger_types']
