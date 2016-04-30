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
from st2common.constants import triggers as trigger_constants
from st2common.util import date as date_utils
from st2common.services import trace as trace_service
from st2common.transport import consumers, reactor
from st2common.transport import utils as transport_utils
import st2reactor.container.utils as container_utils
from st2reactor.rules.engine import RulesEngine


LOG = logging.getLogger(__name__)

RULESENGINE_WORK_Q = reactor.get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine', routing_key='#')


class TriggerInstanceDispatcher(consumers.StagedMessageHandler):
    message_type = dict

    def __init__(self, connection, queues):
        super(TriggerInstanceDispatcher, self).__init__(connection, queues)
        self.rules_engine = RulesEngine()

    def pre_ack_process(self, message):
        '''
        TriggerInstance from message is create prior to acknowledging the message. This
        gets us a way to not acknowledge messages.
        '''
        trigger = message['trigger']
        payload = message['payload']

        # Accomodate for not being able to create a TrigegrInstance if a TriggerDB
        # is not found.
        trigger_instance = container_utils.create_trigger_instance(
            trigger,
            payload or {},
            date_utils.get_datetime_utc_now(),
            raise_on_no_trigger=True)

        return self._compose_pre_ack_process_response(trigger_instance, message)

    def process(self, pre_ack_response):

        trigger_instance, message = self._decompose_pre_ack_process_response(pre_ack_response)
        if not trigger_instance:
            raise ValueError('No trigger_instance provided for processing.')

        try:
            # Use trace_context from the message and if not found create a new context
            # and use the trigger_instance.id as trace_tag.
            trace_context = message.get(TRACE_CONTEXT, None)
            if not trace_context:
                trace_context = {
                    TRACE_ID: 'trigger_instance-%s' % str(trigger_instance.id)
                }
            # add a trace or update an existing trace with trigger_instance
            trace_service.add_or_update_given_trace_context(
                trace_context=trace_context,
                trigger_instances=[
                    trace_service.get_trace_component_for_trigger_instance(trigger_instance)
                ]
            )

            container_utils.update_trigger_instance_status(
                trigger_instance, trigger_constants.TRIGGER_INSTANCE_PROCESSING)
            self.rules_engine.handle_trigger_instance(trigger_instance)
            container_utils.update_trigger_instance_status(
                trigger_instance, trigger_constants.TRIGGER_INSTANCE_PROCESSED)
        except:
            # TODO : Capture the reason for failure.
            container_utils.update_trigger_instance_status(
                trigger_instance, trigger_constants.TRIGGER_INSTANCE_PROCESSING_FAILED)
            # This could be a large message but at least in case of an exception
            # we get to see more context.
            # Beyond this point code cannot really handle the exception anyway so
            # eating up the exception.
            LOG.exception('Failed to handle trigger_instance %s.', trigger_instance)
            return

    @staticmethod
    def _compose_pre_ack_process_response(trigger_instance, message):
        """
        Codify response of the pre_ack_process method.
        """
        return {'trigger_instance': trigger_instance, 'message': message}

    @staticmethod
    def _decompose_pre_ack_process_response(response):
        """
        Break-down response of pre_ack_process into constituents for simpler consumption.
        """
        return response.get('trigger_instance', None), response.get('message', None)


def get_worker():
    with Connection(transport_utils.get_messaging_urls()) as conn:
        return TriggerInstanceDispatcher(conn, [RULESENGINE_WORK_Q])
