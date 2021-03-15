# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
from kombu import Exchange, Queue

from st2common import log as logging
from st2common.constants.trace import TRACE_CONTEXT
from st2common.models.api.trace import TraceContext
from st2common.transport import publishers

__all__ = [
    "TriggerCUDPublisher",
    "TriggerInstancePublisher",
    "TriggerDispatcher",
    "get_sensor_cud_queue",
    "get_trigger_cud_queue",
    "get_trigger_instances_queue",
]

LOG = logging.getLogger(__name__)

# Exchange for Trigger CUD events
TRIGGER_CUD_XCHG = Exchange("st2.trigger", type="topic")

# Exchange for TriggerInstance events
TRIGGER_INSTANCE_XCHG = Exchange("st2.trigger_instances_dispatch", type="topic")

# Exchane for Sensor CUD events
SENSOR_CUD_XCHG = Exchange("st2.sensor", type="topic")


class SensorCUDPublisher(publishers.CUDPublisher):
    """
    Publisher responsible for publishing Trigger model CUD events.
    """

    def __init__(self):
        super(SensorCUDPublisher, self).__init__(exchange=SENSOR_CUD_XCHG)


class TriggerCUDPublisher(publishers.CUDPublisher):
    """
    Publisher responsible for publishing Trigger model CUD events.
    """

    def __init__(self):
        super(TriggerCUDPublisher, self).__init__(exchange=TRIGGER_CUD_XCHG)


class TriggerInstancePublisher(object):
    def __init__(self):
        self._publisher = publishers.PoolPublisher()

    def publish_trigger(self, payload=None, routing_key=None):
        # TODO: We should use trigger reference as a routing key
        self._publisher.publish(payload, TRIGGER_INSTANCE_XCHG, routing_key)


class TriggerDispatcher(object):
    """
    This trigger dispatcher dispatches trigger instances to a message queue (RabbitMQ).
    """

    def __init__(self, logger=LOG):
        self._publisher = TriggerInstancePublisher()
        self._logger = logger

    def dispatch(self, trigger, payload=None, trace_context=None):
        """
        Method which dispatches the trigger.

        :param trigger: Full name / reference of the trigger.
        :type trigger: ``str`` or ``object``

        :param payload: Trigger payload.
        :type payload: ``dict``

        :param trace_context: Trace context to associate with Trigger.
        :type trace_context: ``TraceContext``
        """
        if payload and not isinstance(payload, dict):
            raise TypeError(
                f"The payload has a value that is not a dictionary"
                f" (was {type(payload)})."
            )
        if trace_context and not isinstance(trace_context, TraceContext):
            raise TypeError(
                f"The trace context has a value that is not of type TraceContext"
                f" (was {type(trace_context)})."
            )

        payload = {"trigger": trigger, "payload": payload, TRACE_CONTEXT: trace_context}
        routing_key = "trigger_instance"

        self._logger.debug(
            "Dispatching trigger (trigger=%s,payload=%s)", trigger, payload
        )
        self._publisher.publish_trigger(payload=payload, routing_key=routing_key)


def get_trigger_cud_queue(name, routing_key, exclusive=False):
    return Queue(name, TRIGGER_CUD_XCHG, routing_key=routing_key, exclusive=exclusive)


def get_trigger_instances_queue(name, routing_key):
    return Queue(name, TRIGGER_INSTANCE_XCHG, routing_key=routing_key)


def get_sensor_cud_queue(name, routing_key):
    return Queue(name, SENSOR_CUD_XCHG, routing_key=routing_key)
