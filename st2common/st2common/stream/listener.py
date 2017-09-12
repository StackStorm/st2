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

import eventlet

from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo_config import cfg

from st2common.models.api.action import LiveActionAPI
from st2common.models.api.execution import ActionExecutionAPI
from st2common.models.api.execution import ActionExecutionOutputAPI
from st2common.transport import utils as transport_utils
from st2common.transport.queues import STREAM_ANNOUNCEMENT_WORK_QUEUE
from st2common.transport.queues import STREAM_EXECUTION_ALL_WORK_QUEUE
from st2common.transport.queues import STREAM_EXECUTION_UPDATE_WORK_QUEUE
from st2common.transport.queues import STREAM_LIVEACTION_WORK_QUEUE
from st2common.transport.queues import STREAM_EXECUTION_OUTPUT_QUEUE
from st2common import log as logging

__all__ = [
    'StreamListener',
    'ExecutionOutputListener',

    'get_listener',
    'get_listener_if_set'
]

LOG = logging.getLogger(__name__)


# Stores references to instantiated listeners
_stream_listener = None
_execution_output_listener = None


class BaseListener(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.queues = []
        self._stopped = False

    def get_consumers(self, consumer, channel):
        raise NotImplementedError('get_consumers() is not implemented')

    def processor(self, model=None):
        def process(body, message):
            meta = message.delivery_info
            event_name = '%s__%s' % (meta.get('exchange'), meta.get('routing_key'))

            try:
                if model:
                    body = model.from_model(body, mask_secrets=cfg.CONF.api.mask_secrets)

                self.emit(event_name, body)
            finally:
                message.ack()

        return process

    def emit(self, event, body):
        pack = (event, body)
        for queue in self.queues:
            queue.put(pack)

    def generator(self, events=None, action_refs=None, execution_ids=None):
        queue = eventlet.Queue()
        queue.put('')
        self.queues.append(queue)

        try:
            while not self._stopped:
                try:
                    # TODO: Move to common option
                    message = queue.get(timeout=cfg.CONF.stream.heartbeat)

                    if not message:
                        yield message
                        continue

                    event_name, body = message
                    # TODO: We now do late filtering, but this could also be performed on the
                    # message bus level if we modified our exchange layout and utilize routing keys
                    # Filter on event name
                    if events and event_name not in events:
                        LOG.debug('Skipping event "%s"' % (event_name))
                        continue

                    # Filter on action ref
                    action_ref = self._get_action_ref_for_body(body=body)
                    if action_refs and action_ref not in action_refs:
                        LOG.debug('Skipping event "%s" with action_ref "%s"' % (event_name,
                                                                                action_ref))
                        continue

                    # Filter on execution id
                    execution_id = self._get_execution_id_for_body(body=body)
                    if execution_ids and execution_id not in execution_ids:
                        LOG.debug('Skipping event "%s" with execution_id "%s"' % (event_name,
                                                                                  execution_id))
                        continue

                    yield message
                except eventlet.queue.Empty:
                    yield
        finally:
            self.queues.remove(queue)

    def shutdown(self):
        self._stopped = True

    def _get_action_ref_for_body(self, body):
        """
        Retrieve action_ref for the provided message body.
        """
        if not body:
            return None

        action_ref = None

        if isinstance(body, ActionExecutionAPI):
            action_ref = body.action.get('ref', None) if body.action else None
        elif isinstance(body, LiveActionAPI):
            action_ref = body.action
        elif isinstance(body, (ActionExecutionOutputAPI)):
            action_ref = body.action_ref

        return action_ref

    def _get_execution_id_for_body(self, body):
        if not body:
            return None

        execution_id = None

        if isinstance(body, ActionExecutionAPI):
            execution_id = str(body.id)
        elif isinstance(body, LiveActionAPI):
            execution_id = None
        elif isinstance(body, (ActionExecutionOutputAPI)):
            execution_id = body.execution_id

        return execution_id


class StreamListener(BaseListener):
    """
    Listener used inside stream service.

    It listenes to all the events.
    """

    def get_consumers(self, consumer, channel):
        return [
            consumer(queues=[STREAM_ANNOUNCEMENT_WORK_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor()]),

            consumer(queues=[STREAM_EXECUTION_ALL_WORK_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionAPI)]),

            consumer(queues=[STREAM_LIVEACTION_WORK_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(LiveActionAPI)]),

            consumer(queues=[STREAM_EXECUTION_OUTPUT_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionOutputAPI)])
        ]


class ExecutionOutputListener(BaseListener):
    """
    Listener emitting action execution output event.

    Only listens to action execution work and output queue.
    """

    def get_consumers(self, consumer, channel):
        return [
            consumer(queues=[STREAM_EXECUTION_UPDATE_WORK_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionAPI)]),

            consumer(queues=[STREAM_EXECUTION_OUTPUT_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionOutputAPI)])
        ]


class ExecutionStderrListener(BaseListener):
    """
    Listener used inside action execution /stdout endpoint.

    Only listens to action execution work and stdout queue.
    """

    def get_consumers(self, consumer, channel):
        return [
            consumer(queues=[STREAM_EXECUTION_UPDATE_WORK_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionAPI)]),

            consumer(queues=[STREAM_EXECUTION_STDERR_QUEUE],
                     accept=['pickle'],
                     callbacks=[self.processor(ActionExecutionStderrAPI)])
        ]


def listen(listener):
    try:
        listener.run()
    finally:
        listener.shutdown()


def get_listener(name):
    global _stream_listener
    global _execution_stdout_listener
    global _execution_stderr_listener

    if name == 'stream':
        if not _stream_listener:
            with Connection(transport_utils.get_messaging_urls()) as conn:
                _stream_listener = StreamListener(conn)
                eventlet.spawn_n(listen, _stream_listener)
        return _stream_listener
    elif name == 'execution_output':
        if not _execution_output_listener:
            with Connection(transport_utils.get_messaging_urls()) as conn:
                _execution_stdout_listener = ExecutionOutputListener(conn)
                eventlet.spawn_n(listen, _execution_output_listener)
        return _execution_output_listener
    else:
        raise ValueError('Invalid listener name: %s' % (name))


def get_listener_if_set(name):
    global _stream_listener
    global _execution_stdout_listener
    global _execution_stderr_listener

    if name == 'stream':
        return _stream_listener
    elif name == 'execution_output':
        return _execution_output_listener
    else:
        raise ValueError('Invalid listener name: %s' % (name))
