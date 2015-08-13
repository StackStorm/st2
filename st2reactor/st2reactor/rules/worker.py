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
from st2common.util import date as date_utils
from st2common.transport import consumers, reactor
from st2common.transport import utils as transport_utils
import st2reactor.container.utils as container_utils
from st2reactor.rules.engine import RulesEngine


LOG = logging.getLogger(__name__)

RULESENGINE_WORK_Q = reactor.get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine', routing_key='#')


class TriggerInstanceDispatcher(consumers.MessageHandler):
    message_type = dict

    def __init__(self, connection, queues):
        super(TriggerInstanceDispatcher, self).__init__(connection, queues)
        self.rules_engine = RulesEngine()

    def process(self, instance):
        trigger = instance['trigger']
        payload = instance['payload']

        try:
            trigger_instance = container_utils.create_trigger_instance(
                trigger,
                payload or {},
                date_utils.get_datetime_utc_now())

            if trigger_instance:
                self.rules_engine.handle_trigger_instance(trigger_instance)
            else:
                LOG.info('No trigger found in db for instance. %s', instance)
        except:
            # This could be a large message but at least in case of an exception
            # we get to see more context.
            # Beyond this point code cannot really handle the exception anyway so
            # eating up the exception.
            LOG.exception('Failed to handle trigger_instance %s.', instance)


def get_worker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return TriggerInstanceDispatcher(conn, [RULESENGINE_WORK_Q])
