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
from kombu import Exchange, Queue
from st2common.transport import publishers

ACTIONEXECUTIONSTATE_XCHG = Exchange('st2.actionexecutionstate',
                                     type='topic')


class ActionExecutionStatePublisher(publishers.CUDPublisher):

    def __init__(self, urls):
        super(ActionExecutionStatePublisher, self).__init__(urls, ACTIONEXECUTIONSTATE_XCHG)


def get_queue(name, routing_key):
    return Queue(name, ACTIONEXECUTIONSTATE_XCHG, routing_key=routing_key)
