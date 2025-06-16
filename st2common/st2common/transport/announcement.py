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

from st2common import log as logging
from st2common.constants.trace import TRACE_CONTEXT
from st2common.models.api.trace import TraceContext
from st2common.transport import publishers
from st2common.transport.kombu import Exchange, Queue

__all__ = ["AnnouncementPublisher", "AnnouncementDispatcher", "get_queue"]

LOG = logging.getLogger(__name__)

# Exchange for Announcements
ANNOUNCEMENT_XCHG = Exchange("st2.announcement", type="topic")


class AnnouncementPublisher(object):
    def __init__(self):
        self._publisher = publishers.PoolPublisher()

    def publish(self, payload, routing_key):
        self._publisher.publish(payload, ANNOUNCEMENT_XCHG, routing_key)


class AnnouncementDispatcher(object):
    """
    This announcement dispatcher dispatches announcements to a message queue (RabbitMQ).
    """

    def __init__(self, logger=LOG):
        self._publisher = AnnouncementPublisher()
        self._logger = logger

    def dispatch(self, routing_key, payload, trace_context=None):
        """
        Method which dispatches the announcement.

        :param routing_key: Routing key of the announcement.
        :type routing_key: ``str``

        :param payload: Announcement payload.
        :type payload: ``dict``

        :param trace_context: Trace context to associate with Announcement.
        :type trace_context: ``TraceContext``
        """
        if not isinstance(payload, (type(None), dict)):
            raise TypeError(
                f"The payload has a value that is not a dictionary (was {type(payload)})."
            )
        if not isinstance(trace_context, (type(None), dict, TraceContext)):
            raise TypeError(
                "The trace context has a value that is not a NoneType or dict or TraceContext"
                f" (was {type(trace_context)})."
            )

        payload = {"payload": payload, TRACE_CONTEXT: trace_context}

        self._logger.debug(
            "Dispatching announcement (routing_key=%s,payload=%s)", routing_key, payload
        )
        self._publisher.publish(payload=payload, routing_key=routing_key)


def get_queue(name=None, routing_key="#", exclusive=False, auto_delete=False):
    return Queue(
        name,
        ANNOUNCEMENT_XCHG,
        routing_key=routing_key,
        exclusive=exclusive,
        auto_delete=auto_delete,
    )
