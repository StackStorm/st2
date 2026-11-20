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
import abc
import six

from kombu.mixins import ConsumerMixin
from oslo_config import cfg

from st2common import log as logging
from st2common.transport.connection_retry_mixin import ConnectionRetryMixin
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2common.util import concurrency

__all__ = [
    "QueueConsumer",
    "StagedQueueConsumer",
    "ActionsQueueConsumer",
    "MessageHandler",
    "StagedMessageHandler",
]

LOG = logging.getLogger(__name__)

# Default maximum number of messages a consumer processes at the same time
DEFAULT_CONCURRENCY = 50


class QueueConsumer(ConnectionRetryMixin, ConsumerMixin):
    def __init__(self, connection, queues, handler, concurrency=DEFAULT_CONCURRENCY):
        self.connection = connection
        self._dispatcher = BufferedDispatcher(dispatch_pool_size=concurrency)
        self._queues = queues
        self._handler = handler

        # Initialize connection retry tracking from mixin
        self._init_connection_retry()

    def shutdown(self):
        self.should_stop = True
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(
            queues=self._queues, accept=["pickle"], callbacks=[self.process]
        )

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)

        return [consumer]

    def process(self, body, message):
        try:
            self._validate_message(body)
        except:
            LOG.exception(
                "%s failed to process message: %s", self.__class__.__name__, body
            )
            message.ack()
            return

        dispatcher = self._get_dispatcher(body)

        # Wait for a free slot before acking. Until the message is acked the broker won't
        # deliver the next one (prefetch_count=1), so the backlog stays in the broker instead
        # of piling up in memory.
        if not dispatcher.acquire():
            # Shutting down. The message is not acked so the broker will redeliver it.
            LOG.debug(
                "%s is shutting down, not processing message: %s",
                self.__class__.__name__,
                body,
            )
            return

        try:
            payload = self._pre_ack_process(body)
        except:
            dispatcher.release()
            LOG.exception(
                "%s failed to process message: %s", self.__class__.__name__, body
            )
            message.ack()
            return

        try:
            message.ack()
            dispatcher.dispatch(self._process_message, payload)
        except:
            dispatcher.release()
            raise

    def _validate_message(self, body):
        if not isinstance(body, self._handler.message_type):
            raise TypeError(
                'Received an unexpected type "%s" for payload.' % type(body)
            )

    def _get_dispatcher(self, body):
        return self._dispatcher

    def _pre_ack_process(self, body):
        return body

    def _process_message(self, body):
        try:
            self._handler.process(body)
        except:
            LOG.exception(
                "%s failed to process message: %s", self.__class__.__name__, body
            )


class StagedQueueConsumer(QueueConsumer):
    """
    Used by ``StagedMessageHandler`` to effectively manage it 2 step message handling.
    """

    def _pre_ack_process(self, body):
        return self._handler.pre_ack_process(body)


class ActionsQueueConsumer(QueueConsumer):
    """
    Special Queue Consumer for action runner which uses multiple BufferedDispatcher pools:

    1. For regular (non-workflow) actions
    2. One for workflow actions

    This way workflow actions get their own slots and can't use up the slots for non-workflow
    actions. Both pools are fed by the same consumer though, so while the pool needed by the
    next message is full, no more messages are pulled from the queue for either pool.
    """

    def __init__(self, connection, queues, handler):
        super(ActionsQueueConsumer, self).__init__(connection, queues, handler)

        # Override the single dispatcher with two specialized dispatchers
        workflows_pool_size = cfg.CONF.actionrunner.workflows_pool_size
        actions_pool_size = cfg.CONF.actionrunner.actions_pool_size
        self._workflows_dispatcher = BufferedDispatcher(
            dispatch_pool_size=workflows_pool_size, name="workflows-dispatcher"
        )
        self._actions_dispatcher = BufferedDispatcher(
            dispatch_pool_size=actions_pool_size, name="actions-dispatcher"
        )

    def _get_dispatcher(self, body):
        action_is_workflow = getattr(body, "action_is_workflow", False)
        if action_is_workflow:
            # Use workflow dispatcher queue
            dispatcher = self._workflows_dispatcher
        else:
            # Use queue for regular or workflow actions
            dispatcher = self._actions_dispatcher

        LOG.debug('Using BufferedDispatcher pool: "%s"', str(dispatcher))
        return dispatcher

    def shutdown(self):
        self._workflows_dispatcher.shutdown()
        self._actions_dispatcher.shutdown()
        self.should_stop = True


class VariableMessageQueueConsumer(QueueConsumer):
    """
    Used by ``VariableMessageHandler`` to processes multiple message types.
    """

    def _validate_message(self, body):
        if not self._handler.message_types.get(type(body)):
            raise TypeError(
                'Received an unexpected type "%s" for payload.' % type(body)
            )


@six.add_metaclass(abc.ABCMeta)
class MessageHandler(object):
    message_type = None

    def __init__(self, connection, queues):
        self._queue_consumer = self.get_queue_consumer(
            connection=connection, queues=queues
        )
        self._consumer_thread = None

    def start(self, wait=False):
        LOG.info("Starting %s...", self.__class__.__name__)
        self._consumer_thread = concurrency.spawn(self._queue_consumer.run)

        if wait:
            self.wait()

    def wait(self):
        return concurrency.wait(self._consumer_thread)

    def shutdown(self):
        LOG.info("Shutting down %s...", self.__class__.__name__)
        self._queue_consumer.shutdown()

    def kill(self):
        concurrency.kill(self._consumer_thread, SystemExit())

    @abc.abstractmethod
    def process(self, message):
        pass

    def get_concurrency(self):
        """
        Maximum number of messages this handler processes at the same time. Messages beyond
        that are left in the queue until a running one completes.
        """
        return DEFAULT_CONCURRENCY

    def get_queue_consumer(self, connection, queues):
        return QueueConsumer(
            connection=connection,
            queues=queues,
            handler=self,
            concurrency=self.get_concurrency(),
        )


@six.add_metaclass(abc.ABCMeta)
class StagedMessageHandler(MessageHandler):
    """
    MessageHandler to deal with messages in 2 steps.
        1. pre_ack_process : This is called on the handler before ack-ing the message.
        2. process: Called after ack-in the messages
    This 2 step approach provides a way for the handler to do some hadling like saving to DB etc
    before acknowleding and then performing future processing async. This way even if the handler
    or owning process is taken down system will still maintain track of the message.
    """

    @abc.abstractmethod
    def pre_ack_process(self, message):
        """
        Called before acknowleding a message. Good place to track the message via a DB entry or some
        other applicable mechnism.

        The reponse of this method is passed into the ``process`` method. This was whatever is the
        processed version of the message can be moved forward. It is always possible to simply
        return ``message`` and have ``process`` handle the original message.
        """
        pass

    def get_queue_consumer(self, connection, queues):
        return StagedQueueConsumer(
            connection=connection,
            queues=queues,
            handler=self,
            concurrency=self.get_concurrency(),
        )


@six.add_metaclass(abc.ABCMeta)
class VariableMessageHandler(MessageHandler):
    """
    VariableMessageHandler processes multiple message types.
    """

    def get_queue_consumer(self, connection, queues):
        return VariableMessageQueueConsumer(
            connection=connection,
            queues=queues,
            handler=self,
            concurrency=self.get_concurrency(),
        )
