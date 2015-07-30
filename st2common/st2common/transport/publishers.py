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
from kombu.messaging import Producer

from st2common import log as logging

ANY_RK = '*'
CREATE_RK = 'create'
UPDATE_RK = 'update'
DELETE_RK = 'delete'

LOG = logging.getLogger(__name__)


class PoolPublisher(object):
    def __init__(self, urls):
        self.pool = Connection(urls, failover_strategy='round-robin').Pool(limit=10)

    def errback(self, exc, interval):
        LOG.error('Rabbitmq connection error: %s', exc.message, exc_info=False)

    def publish(self, payload, exchange, routing_key=''):
        # pickling the payload for now. Better serialization mechanism is essential.
        with self.pool.acquire(block=True) as connection:
            should_stop = False
            while not should_stop:
                # creating a new channel for every producer publish. This could be expensive
                # and maybe there is a better way to do this by creating a ChannelPool etc.
                channel = connection.channel()
                # ProducerPool ends up creating it own ConnectionPool which ends up completely
                # invalidating this ConnectionPool. Also, a ConnectionPool for producer does not
                # really solve any problems for us so better to create a Producer for each publish.
                # Producers anyway use the provided channel objects so safe to create one per publish.
                producer = Producer(channel)
                try:
                    publish_func = connection.ensure(producer, producer.publish,
                                                     errback=self.errback,
                                                     max_retries=3)
                    publish_func(payload, exchange=exchange, routing_key=routing_key,
                                 serializer='pickle')
                    should_stop = True
                except connection.connection_errors + connection.channel_errors:
                    LOG.exception('Connection or channel error identified.')
                    connection.close()
                    connection.ensure_connection()
                    channel = connection.channel()
                except Exception as e:
                    LOG.error('Connections to rabbitmq cannot be re-established: %s', e.message)
                    should_stop = True
                finally:
                    if should_stop and channel:
                        try:
                            channel.close()
                        except Exception:
                            LOG.warning('Error closing channel.', exc_info=True)


class CUDPublisher(object):
    def __init__(self, urls, exchange):
        self._publisher = PoolPublisher(urls=urls)
        self._exchange = exchange

    def publish_create(self, payload):
        self._publisher.publish(payload, self._exchange, CREATE_RK)

    def publish_update(self, payload):
        self._publisher.publish(payload, self._exchange, UPDATE_RK)

    def publish_delete(self, payload):
        self._publisher.publish(payload, self._exchange, DELETE_RK)


class StatePublisherMixin(object):
    def __init__(self, urls, exchange):
        self._state_publisher = PoolPublisher(urls=urls)
        self._state_exchange = exchange

    def publish_state(self, payload, state):
        if not state:
            raise Exception('Unable to publish unassigned state.')

        self._state_publisher.publish(payload, self._state_exchange, state)
