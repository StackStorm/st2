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

# All Exchanges and Queues related to liveaction.

from __future__ import absolute_import

import kombu

from st2common.transport import publishers

__all__ = [
    'WorkflowExecutionPublisher',
    'get_queue'
]

WORKFLOW_EXECUTION_XCHG = kombu.Exchange('st2.workflow', type='topic')
WORKFLOW_EXECUTION_STATUS_MGMT_XCHG = kombu.Exchange('st2.workflow.status', type='topic')


class WorkflowExecutionPublisher(publishers.CUDPublisher, publishers.StatePublisherMixin):

    def __init__(self, urls):
        publishers.CUDPublisher.__init__(self, urls, WORKFLOW_EXECUTION_XCHG)
        publishers.StatePublisherMixin.__init__(self, urls, WORKFLOW_EXECUTION_STATUS_MGMT_XCHG)


def get_queue(name, routing_key):
    return kombu.Queue(name, WORKFLOW_EXECUTION_XCHG, routing_key=routing_key)


def get_status_management_queue(name, routing_key):
    return kombu.Queue(name, WORKFLOW_EXECUTION_STATUS_MGMT_XCHG, routing_key=routing_key)
