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

LOG = logging.getLogger('st2common.transport.bootstrap')

__all__ = [
    'register_exchanges'
]

EXCHANGES = [ACTIONEXECUTIONSTATE_XCHG, ANNOUNCEMENT_XCHG, EXECUTION_XCHG, LIVEACTION_XCHG,
             LIVEACTION_STATUS_MGMT_XCHG, TRIGGER_CUD_XCHG, TRIGGER_INSTANCE_XCHG,
             SENSOR_CUD_XCHG]


def _do_register_exchange(exchange, connection, channel, retry_wrapper):
    try:
        kwargs = {
            'exchange': exchange.name,
            'type': exchange.type,
            'durable': exchange.durable,
            'auto_delete': exchange.auto_delete,
            'arguments': exchange.arguments,
            'nowait': False,
            'passive': None
        }
        # Use the retry wrapper to increase resiliency in recoverable errors.
        retry_wrapper.ensured(connection=connection,
                              obj=channel,
                              to_ensure_func=channel.exchange_declare,
                              **kwargs)
        LOG.debug('registered exchange %s.', exchange.name)
    except Exception:
        LOG.exception('Failed to register exchange : %s.', exchange.name)


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
