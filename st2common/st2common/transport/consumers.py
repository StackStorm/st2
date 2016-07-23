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

import abc
import eventlet
import six

from kombu.mixins import ConsumerMixin
from oslo_config import cfg

from st2common import log as logging
from st2common.util.greenpooldispatch import BufferedDispatcher

__all__ = [
    'QueueConsumer',
    'StagedQueueConsumer',
    'ActionsQueueConsumer',

    'MessageHandler',
    'StagedMessageHandler'
]

LOG = logging.getLogger(__name__)


class QueueConsumer(ConsumerMixin):
    def __init__(self, connection, queues, handler):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()
        self._queues = queues
        self._handler = handler

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=self._queues, accept=['pickle'], callbacks=[self.process])

        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)

        return [consumer]

    def process(self, body, message):
        try:
            if not isinstance(body, self._handler.message_type):
                raise TypeError('Received an unexpected type "%s" for payload.' % type(body))

            self._dispatcher.dispatch(self._process_message, body)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)
        finally:
            # At this point we will always ack a message.
            message.ack()

    def _process_message(self, body):
        try:
            self._handler.process(body)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)


class StagedQueueConsumer(QueueConsumer):
    """
    Used by ``StagedMessageHandler`` to effectively manage it 2 step message handling.
    """

    def process(self, body, message):
        try:
            if not isinstance(body, self._handler.message_type):
                raise TypeError('Received an unexpected type "%s" for payload.' % type(body))
            response = self._handler.pre_ack_process(body)
            self._dispatcher.dispatch(self._process_message, response)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)
        finally:
            # At this point we will always ack a message.
            message.ack()


class ActionsQueueConsumer(QueueConsumer):
    """
    Special Queue Consumer for action runner which uses multiple BufferedDispatcher pools:

    1. For regular (non-workflow) actions
    2. One for workflow actions

    This way we can ensure workflow actions never block non-workflow actions.
    """

    def __init__(self, connection, queues, handler):
        self.connection = connection

        self._queues = queues
        self._handler = handler

        workflows_pool_size = cfg.CONF.actionrunner.workflows_pool_size
        actions_pool_size = cfg.CONF.actionrunner.actions_pool_size
        self._workflows_dispatcher = BufferedDispatcher(dispatch_pool_size=workflows_pool_size,
                                                        name='workflows-dispatcher')
        self._actions_dispatcher = BufferedDispatcher(dispatch_pool_size=actions_pool_size,
                                                      name='actions-dispatcher')

    def process(self, body, message):
        try:
            if not isinstance(body, self._handler.message_type):
                raise TypeError('Received an unexpected type "%s" for payload.' % type(body))

            action_is_workflow = getattr(body, 'action_is_workflow', False)
            if action_is_workflow:
                # Use workflow dispatcher queue
                dispatcher = self._workflows_dispatcher
            else:
                # Use queue for regular or workflow actions
                dispatcher = self._actions_dispatcher

            LOG.debug('Using BufferedDispatcher pool: "%s"', str(dispatcher))
            dispatcher.dispatch(self._process_message, body)
        except:
            LOG.exception('%s failed to process message: %s', self.__class__.__name__, body)
        finally:
            # At this point we will always ack a message.
            message.ack()

    def shutdown(self):
        self._workflows_dispatcher.shutdown()
        self._actions_dispatcher.shutdown()


@six.add_metaclass(abc.ABCMeta)
class MessageHandler(object):
    message_type = None

    def __init__(self, connection, queues):
        self._queue_consumer = self.get_queue_consumer(connection=connection,
                                                       queues=queues)
        self._consumer_thread = None

    def start(self, wait=False):
        LOG.info('Starting %s...', self.__class__.__name__)
        self._consumer_thread = eventlet.spawn(self._queue_consumer.run)

        if wait:
            self.wait()

    def wait(self):
        self._consumer_thread.wait()

    def shutdown(self):
        LOG.info('Shutting down %s...', self.__class__.__name__)
        self._queue_consumer.shutdown()

    @abc.abstractmethod
    def process(self, message):
        pass

    def get_queue_consumer(self, connection, queues):
        return QueueConsumer(connection=connection, queues=queues, handler=self)


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
        return StagedQueueConsumer(connection=connection, queues=queues, handler=self)
