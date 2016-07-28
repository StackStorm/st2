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

from st2client.models import Pack
from st2client.commands import resource


class PackBranch(resource.ResourceBranch):
    def __init__(self, description, app, subparsers, parent_parser=None):
        super(PackBranch, self).__init__(
            Pack, description, app, subparsers,
            parent_parser=parent_parser,
            read_only=True,
            commands={
                'list': PackListCommand
            })

        self.commands['install'] = PackInstallCommand(self.resource, self.app, self.subparsers)
        self.commands['uninstall'] = PackUninstallCommand(self.resource, self.app, self.subparsers)
        self.commands['register'] = PackRegisterCommand(self.resource, self.app, self.subparsers)


class PackInstallCommand(resource.ContentPackResourceListCommand):
    display_attributes = ['all']


class PackUninstallCommand(resource.ContentPackResourceGetCommand):
    display_attributes = ['all']


class PackRegisterCommand(resource.ContentPackResourceEnableCommand):
    display_attributes = ['all']
