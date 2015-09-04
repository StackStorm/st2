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

from st2api.controllers.resource import ResourceController
from st2common.models.api.trace import TraceAPI
from st2common.persistence.trace import Trace

__all__ = [
    'TracesController'
]


class TracesController(ResourceController):
    model = TraceAPI
    access = Trace
    supported_filters = {
        'trace_tag': 'trace_tag',
        'execution': 'action_executions.object_id',
        'rule': 'rules.object_id',
        'trigger_instance': 'trigger_instances.object_id',
    }

    query_options = {
        'sort': ['trace_tag']
    }
