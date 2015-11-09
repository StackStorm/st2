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

from st2common import log as logging
from st2common.constants.trace import TRACE_CONTEXT
from st2common.models.api.trace import TraceContext
from st2common.transport import publishers
from st2common.transport import utils as transport_utils

LOG = logging.getLogger(__name__)

# Exchange for Announcements
ANNOUNCEMENT_XCHG = Exchange('st2.announcement', type='topic')


class AnnouncementPublisher(object):
    def __init__(self, urls):
        self._publisher = publishers.PoolPublisher(urls=urls)

    def publish(self, payload, routing_key):
        self._publisher.publish(payload, ANNOUNCEMENT_XCHG, routing_key)


class AnnouncementDispatcher(object):
    """
    This announcement dispatcher dispatches announcements to a message queue (RabbitMQ).
    """

    def __init__(self, logger=LOG):
        self._publisher = AnnouncementPublisher(urls=transport_utils.get_messaging_urls())
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
        assert isinstance(payload, (type(None), dict))
        assert isinstance(trace_context, (type(None), TraceContext))

        payload = {
            'payload': payload,
            TRACE_CONTEXT: trace_context
        }

        self._logger.debug('Dispatching announcement (routing_key=%s,payload=%s)',
                           routing_key, payload)
        self._publisher.publish(payload=payload, routing_key=routing_key)


def get_queue(name=None, routing_key='#', exclusive=False):
    return Queue(name, ANNOUNCEMENT_XCHG, routing_key=routing_key, exclusive=exclusive)
