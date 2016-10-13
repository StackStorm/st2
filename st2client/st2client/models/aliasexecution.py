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

from st2client.models import core

__all__ = [
    'ActionAliasExecution'
]


class ActionAliasExecution(core.Resource):
    _alias = 'Action-Alias-Execution'
    _display_name = 'ActionAlias Execution'
    _plural = 'ActionAliasExecutions'
    _plural_display_name = 'Runners'
    _url_path = 'aliasexecution'
    _repr_attributes = ['name', 'format', 'command', 'user', 'source_channel',
                        'notification_channel', 'notification_route']
