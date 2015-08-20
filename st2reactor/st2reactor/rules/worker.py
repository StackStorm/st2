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
from st2common.constants.trace import TRACE_CONTEXT, TRACE_ID
from st2common.util import date as date_utils
from st2common.services.trace import add_or_update_given_trace_context
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

        trigger_instance = None
        try:
            trigger_instance = container_utils.create_trigger_instance(
                trigger,
                payload or {},
                date_utils.get_datetime_utc_now(),
                raise_on_no_trigger=True)
        except:
            # We got a trigger ref but we were unable to create a trigger instance.
            # This could be because a trigger object wasn't found in db for the ref.
            LOG.exception('Failed to create trigger_instance %s.', instance)
            return

        if trigger_instance:
            try:
                # Use trace_context from the instance and if not found create a new context
                # and use the trigger_instance.id as trace_tag.
                trace_context = instance.get(TRACE_CONTEXT, None)
                if not trace_context:
                    trace_context = {
                        TRACE_ID: 'trigger_instance-%s' % str(trigger_instance.id)
                    }
                # add a trace or update an existing trace with trigger_instance
                add_or_update_given_trace_context(trace_context=trace_context,
                                                  trigger_instances=[str(trigger_instance.id)])
                self.rules_engine.handle_trigger_instance(trigger_instance)
            except:
                # This could be a large message but at least in case of an exception
                # we get to see more context.
                # Beyond this point code cannot really handle the exception anyway so
                # eating up the exception.
                LOG.exception('Failed to handle trigger_instance %s.', instance)
                return


def get_worker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return TriggerInstanceDispatcher(conn, [RULESENGINE_WORK_Q])
