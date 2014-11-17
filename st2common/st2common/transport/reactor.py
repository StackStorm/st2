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

from kombu import Exchange, Queue

from st2common.transport import publishers

__all__ = [
    'TriggerCUDPublisher',
    'TriggerPublisher',

    'get_trigger_cud_queue',
    'get_trigger_queue'
]

# Exchange for Trigger CUD events
TRIGGER_CUD_XCHG = Exchange('st2.trigger', type='topic')

# Exchange for Trigger events
TRIGGER_XCHG = Exchange('st2.trigger_dispatch', type='topic')


class TriggerCUDPublisher(publishers.CUDPublisher):
    """
    Publisher responsible for publishing Trigger model CUD events.
    """

    def __init__(self, url):
        super(TriggerCUDPublisher, self).__init__(url, TRIGGER_CUD_XCHG)


class TriggerPublisher(object):
    def __init__(self, url):
        self._publisher = publishers.PoolPublisher(url=url)

    def publish_trigger(self, payload, routing_key):
        # TODO: We could use trigger reference as a routing key
        self._publisher.publish(payload, TRIGGER_XCHG, routing_key)


def get_trigger_cud_queue(name, routing_key):
    return Queue(name, TRIGGER_CUD_XCHG, routing_key=routing_key)


def get_trigger_queue(name, routing_key):
    return Queue(name, TRIGGER_XCHG, routing_key=routing_key)
