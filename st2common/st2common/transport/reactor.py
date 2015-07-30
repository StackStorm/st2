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

from oslo_config import cfg

from st2common import log as logging
from st2common.transport import publishers

__all__ = [
    'TriggerCUDPublisher',
    'TriggerInstancePublisher',

    'TriggerDispatcher',

    'get_sensor_cud_queue',
    'get_trigger_cud_queue',
    'get_trigger_instances_queue'
]

LOG = logging.getLogger(__name__)

# Exchange for Trigger CUD events
TRIGGER_CUD_XCHG = Exchange('st2.trigger', type='topic')

# Exchange for TriggerInstance events
TRIGGER_INSTANCE_XCHG = Exchange('st2.trigger_instances_dispatch', type='topic')

# Exchane for Sensor CUD events
SENSOR_CUD_XCHG = Exchange('st2.sensor', type='topic')


class SensorCUDPublisher(publishers.CUDPublisher):
    """
    Publisher responsible for publishing Trigger model CUD events.
    """

    def __init__(self, url):
        super(SensorCUDPublisher, self).__init__(url, SENSOR_CUD_XCHG)


class TriggerCUDPublisher(publishers.CUDPublisher):
    """
    Publisher responsible for publishing Trigger model CUD events.
    """

    def __init__(self, url):
        super(TriggerCUDPublisher, self).__init__(url, TRIGGER_CUD_XCHG)


class TriggerInstancePublisher(object):
    def __init__(self, url):
        self._publisher = publishers.PoolPublisher(url=url)

    def publish_trigger(self, payload=None, routing_key=None):
        # TODO: We should use trigger reference as a routing key
        self._publisher.publish(payload, TRIGGER_INSTANCE_XCHG, routing_key)


class TriggerDispatcher(object):
    """
    This trigger dispatcher dispatches trigger instances to a message queue (RabbitMQ).
    """

    def __init__(self, logger=LOG):
        self._publisher = TriggerInstancePublisher(url=cfg.CONF.messaging.url)
        self._logger = logger

    def dispatch(self, trigger, payload=None):
        """
        Method which dispatches the trigger.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str`` or ``object``

        :param payload: Trigger payload.
        :type payload: ``dict``
        """
        assert isinstance(payload, (type(None), dict))

        payload = {
            'trigger': trigger,
            'payload': payload
        }
        routing_key = 'trigger_instance'

        self._logger.debug('Dispatching trigger (trigger=%s,payload=%s)', trigger, payload)
        self._publisher.publish_trigger(payload=payload, routing_key=routing_key)


def get_trigger_cud_queue(name, routing_key):
    return Queue(name, TRIGGER_CUD_XCHG, routing_key=routing_key)


def get_trigger_instances_queue(name, routing_key):
    return Queue(name, TRIGGER_INSTANCE_XCHG, routing_key=routing_key)


def get_sensor_cud_queue(name, routing_key):
    return Queue(name, SENSOR_CUD_XCHG, routing_key=routing_key)
