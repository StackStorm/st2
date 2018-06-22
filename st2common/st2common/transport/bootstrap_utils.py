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

from __future__ import absolute_import
import socket

import retrying
from oslo_config import cfg
from kombu import Connection

from st2common import log as logging
from st2common.transport import utils as transport_utils
from st2common.transport.actionexecutionstate import ACTIONEXECUTIONSTATE_XCHG
from st2common.transport.announcement import ANNOUNCEMENT_XCHG
from st2common.transport.connection_retry_wrapper import ConnectionRetryWrapper
from st2common.transport.execution import EXECUTION_XCHG
from st2common.transport.liveaction import LIVEACTION_XCHG, LIVEACTION_STATUS_MGMT_XCHG
from st2common.transport.reactor import SENSOR_CUD_XCHG
from st2common.transport.reactor import TRIGGER_CUD_XCHG, TRIGGER_INSTANCE_XCHG
from st2common.transport import reactor
from st2common.transport.workflow import WORKFLOW_EXECUTION_XCHG
from st2common.transport.workflow import WORKFLOW_EXECUTION_STATUS_MGMT_XCHG
from st2common.transport.queues import ACTIONSCHEDULER_REQUEST_QUEUE
from st2common.transport.queues import ACTIONRUNNER_WORK_QUEUE
from st2common.transport.queues import ACTIONRUNNER_CANCEL_QUEUE
from st2common.transport.queues import NOTIFIER_ACTIONUPDATE_WORK_QUEUE
from st2common.transport.queues import RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE
from st2common.transport.queues import RULESENGINE_WORK_QUEUE
from st2common.transport.queues import STREAM_ANNOUNCEMENT_WORK_QUEUE
from st2common.transport.queues import STREAM_EXECUTION_ALL_WORK_QUEUE
from st2common.transport.queues import STREAM_LIVEACTION_WORK_QUEUE
from st2common.transport.queues import STREAM_EXECUTION_OUTPUT_QUEUE
from st2common.transport.queues import WORKFLOW_EXECUTION_WORK_QUEUE
from st2common.transport.queues import WORKFLOW_EXECUTION_RESUME_QUEUE

LOG = logging.getLogger('st2common.transport.bootstrap')

__all__ = [
    'register_exchanges',

    'EXCHANGES',
    'QUEUES'
]

# List of exchanges which are pre-declared on service set up.
EXCHANGES = [
    ACTIONEXECUTIONSTATE_XCHG,
    ANNOUNCEMENT_XCHG,
    EXECUTION_XCHG,
    LIVEACTION_XCHG,
    LIVEACTION_STATUS_MGMT_XCHG,
    TRIGGER_CUD_XCHG,
    TRIGGER_INSTANCE_XCHG,
    SENSOR_CUD_XCHG,
    WORKFLOW_EXECUTION_XCHG,
    WORKFLOW_EXECUTION_STATUS_MGMT_XCHG
]

# List of queues which are pre-declared on service startup.
# All the queues need to be declared and bound up front so we can guarantee messages get routed
# and don't get lost even if there are no consumers online
QUEUES = [
    ACTIONSCHEDULER_REQUEST_QUEUE,
    ACTIONRUNNER_WORK_QUEUE,
    ACTIONRUNNER_CANCEL_QUEUE,
    NOTIFIER_ACTIONUPDATE_WORK_QUEUE,
    RESULTSTRACKER_ACTIONSTATE_WORK_QUEUE,
    RULESENGINE_WORK_QUEUE,

    STREAM_ANNOUNCEMENT_WORK_QUEUE,
    STREAM_EXECUTION_ALL_WORK_QUEUE,
    STREAM_LIVEACTION_WORK_QUEUE,
    STREAM_EXECUTION_OUTPUT_QUEUE,

    WORKFLOW_EXECUTION_WORK_QUEUE,
    WORKFLOW_EXECUTION_RESUME_QUEUE,

    # Those queues are dynamically / late created on some class init but we still need to
    # pre-declare them for redis Kombu backend to work.
    reactor.get_trigger_cud_queue(name='st2.preinit', routing_key='init'),
    reactor.get_sensor_cud_queue(name='st2.preinit', routing_key='init')
]


def _do_register_exchange(exchange, connection, channel, retry_wrapper):
    try:
        kwargs = {
            'exchange': exchange.name,
            'type': exchange.type,
            'durable': exchange.durable,
            'auto_delete': exchange.auto_delete,
            'arguments': exchange.arguments,
            'nowait': False,
            'passive': False
        }
        # Use the retry wrapper to increase resiliency in recoverable errors.
        retry_wrapper.ensured(connection=connection,
                              obj=channel,
                              to_ensure_func=channel.exchange_declare,
                              **kwargs)
        LOG.debug('Registered exchange %s (%s).' % (exchange.name, str(kwargs)))
    except Exception:
        LOG.exception('Failed to register exchange: %s.', exchange.name)


def _do_predeclare_queue(channel, queue):
    LOG.debug('Predeclaring queue for exchange "%s"' % (queue.exchange.name))

    bound_queue = None

    try:
        bound_queue = queue(channel)
        bound_queue.declare(nowait=False)
        LOG.debug('Predeclared queue for exchange "%s"' % (queue.exchange.name))
    except Exception:
        LOG.exception('Failed to predeclare queue for exchange "%s"' % (queue.exchange.name))

    return bound_queue


def register_exchanges():
    LOG.debug('Registering exchanges...')
    connection_urls = transport_utils.get_messaging_urls()
    with Connection(connection_urls) as conn:
        # Use ConnectionRetryWrapper to deal with rmq clustering etc.
        retry_wrapper = ConnectionRetryWrapper(cluster_size=len(connection_urls), logger=LOG)

        def wrapped_register_exchanges(connection, channel):
            for exchange in EXCHANGES:
                _do_register_exchange(exchange=exchange, connection=connection, channel=channel,
                                      retry_wrapper=retry_wrapper)

        retry_wrapper.run(connection=conn, wrapped_callback=wrapped_register_exchanges)

        def wrapped_predeclare_queues(connection, channel):
            for queue in QUEUES:
                _do_predeclare_queue(channel=channel, queue=queue)

        retry_wrapper.run(connection=conn, wrapped_callback=wrapped_predeclare_queues)


def register_exchanges_with_retry():
    def retry_if_io_error(exception):
        return isinstance(exception, socket.error)

    retrying_obj = retrying.Retrying(
        retry_on_exception=retry_if_io_error,
        wait_fixed=cfg.CONF.messaging.connection_retry_wait,
        stop_max_attempt_number=cfg.CONF.messaging.connection_retries
    )
    return retrying_obj.call(register_exchanges)
