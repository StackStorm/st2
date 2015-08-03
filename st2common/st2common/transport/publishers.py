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

import copy
import eventlet

from kombu import Connection
from kombu.messaging import Producer

from st2common import log as logging

ANY_RK = '*'
CREATE_RK = 'create'
UPDATE_RK = 'update'
DELETE_RK = 'delete'

LOG = logging.getLogger(__name__)


class ClusterRetryContext(object):
    """
    Stores retry context for cluster retries. It makes certain assumptions
    on how cluster_size and retry should be determined.
    """
    def __init__(self, cluster_size):
        # No of nodes in a cluster
        self.cluster_size = cluster_size
        # No of times to retry in a cluster
        self.cluster_retry = 2
        # time to wait between retry in a cluster
        self.wait_between_cluster = 10

        # No of nodes attempted. Starts at 1 since the
        self._nodes_attempted = 1

    def test_should_stop(self):
        should_stop = True
        if self._nodes_attempted > self.cluster_size * self.cluster_retry:
            return should_stop, -1
        wait = 0
        should_stop = False
        if self._nodes_attempted % self.cluster_size == 0:
            wait = self.wait_between_cluster
        self._nodes_attempted += 1
        return should_stop, wait


class PoolPublisher(object):
    def __init__(self, urls):
        self.pool = Connection(urls, failover_strategy='round-robin').Pool(limit=10)
        self.cluster_size = len(urls)

    def errback(self, exc, interval):
        LOG.error('Rabbitmq connection error: %s', exc.message, exc_info=False)

    def publish(self, payload, exchange, routing_key=''):
        # pickling the payload for now. Better serialization mechanism is essential.
        with self.pool.acquire(block=True) as connection:
            retry_context = ClusterRetryContext(cluster_size=self.cluster_size)
            should_stop = False
            channel = None
            while not should_stop:
                try:
                    # creating a new channel for every producer publish. This could be expensive
                    # and maybe there is a better way to do this by creating a ChannelPool etc.
                    channel = connection.channel()
                    # ProducerPool ends up creating it own ConnectionPool which ends up completely
                    # invalidating this ConnectionPool. Also, a ConnectionPool for producer does not
                    # really solve any problems for us so better to create a Producer for each
                    # publish.
                    producer = Producer(channel)
                    publish_func = connection.ensure(producer, producer.publish,
                                                     errback=self.errback,
                                                     max_retries=3)
                    publish_func(payload, exchange=exchange, routing_key=routing_key,
                                 serializer='pickle')
                    should_stop = True
                except connection.connection_errors + connection.channel_errors as e:
                    LOG.error('Connection or channel error identified.')
                    should_stop, wait = retry_context.test_should_stop()
                    # reset channel to None to avoid any channel closing errors. At this point
                    # in case of an exception there should be no channel but that is better to
                    # guarantee.
                    channel = None
                    # All attempts to re-establish connections have failed. This error needs to
                    # be notified so raise.
                    if should_stop:
                        raise
                    # -1, 0 and 1+ are handled properly by eventlet.sleep
                    eventlet.sleep(wait)

                    connection.close()
                    # ensure_connection will automatically switch to an alternate. Other connections
                    # in the pool will be fixed independently. It would be nice to cut-over the
                    # entire ConnectionPool simultaneously but that would require writing our own
                    # ConnectionPool. If a server recovers it could happen that the same process
                    # ends up talking to separate nodes in a cluster.
                    connection.ensure_connection()

                except Exception as e:
                    LOG.error('Connections to rabbitmq cannot be re-established: %s', e.message)
                    # Not being able to publish a message could be a significant issue for an app.
                    raise
                finally:
                    if should_stop and channel:
                        try:
                            channel.close()
                        except Exception:
                            LOG.warning('Error closing channel.', exc_info=True)


class SharedPoolPublishers(object):
    """
    This maintains some shared PoolPublishers. Within a single process the configured AMQP
    server is usually the same. This sharing allows from the same PoolPublisher to be reused
    for publishing purposes. Sharing publishers leads to shared connections.
    """
    shared_publishers = {}

    def get_publisher(self, urls):
        # The publisher_key format here only works because we are aware that urls will be a
        # list of strings. Sorting to end up with the same PoolPublisher regardless of
        # ordering in supplied list.
        urls_copy = copy.copy(urls)
        urls_copy.sort()
        publisher_key = ''.join(urls_copy)
        publisher = self.shared_publishers.get(publisher_key, None)
        if not publisher:
            # Use original urls here to preserve order.
            publisher = PoolPublisher(urls=urls)
            self.shared_publishers[publisher_key] = publisher
        return publisher


class CUDPublisher(object):
    def __init__(self, urls, exchange):
        self._publisher = SharedPoolPublishers().get_publisher(urls=urls)
        self._exchange = exchange

    def publish_create(self, payload):
        self._publisher.publish(payload, self._exchange, CREATE_RK)

    def publish_update(self, payload):
        self._publisher.publish(payload, self._exchange, UPDATE_RK)

    def publish_delete(self, payload):
        self._publisher.publish(payload, self._exchange, DELETE_RK)


class StatePublisherMixin(object):
    def __init__(self, urls, exchange):
        self._state_publisher = SharedPoolPublishers().get_publisher(urls=urls)
        self._state_exchange = exchange

    def publish_state(self, payload, state):
        if not state:
            raise Exception('Unable to publish unassigned state.')

        self._state_publisher.publish(payload, self._state_exchange, state)
