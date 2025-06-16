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

import copy

from kombu.messaging import Producer
from oslo_config import cfg

from st2common import log as logging
from st2common.metrics.base import Timer
from st2common.transport import utils as transport_utils
from st2common.transport.connection_retry_wrapper import ConnectionRetryWrapper

__all__ = [
    "PoolPublisher",
    "SharedPoolPublishers",
    "CUDPublisher",
    "StatePublisherMixin",
]

ANY_RK = "*"
CREATE_RK = "create"
UPDATE_RK = "update"
DELETE_RK = "delete"

LOG = logging.getLogger(__name__)


class PoolPublisher(object):
    def __init__(self, urls=None):
        """
        :param urls: Connection URLs to use. If not provided it uses a default value from
                     the config.
        :type urls: ``list``
        """
        urls = urls or transport_utils.get_messaging_urls()
        connection = transport_utils.get_connection(
            urls=urls, connection_kwargs={"failover_strategy": "round-robin"}
        )
        self.pool = connection.Pool(limit=10)
        self.cluster_size = len(urls)

    def errback(self, exc, interval):
        LOG.error("Rabbitmq connection error: %s", exc.message, exc_info=False)

    def publish(self, payload, exchange, routing_key="", compression=None):
        compression = compression or cfg.CONF.messaging.compression

        with Timer(key="amqp.pool_publisher.publish_with_retries." + exchange.name):
            with self.pool.acquire(block=True) as connection:
                retry_wrapper = ConnectionRetryWrapper(
                    cluster_size=self.cluster_size, logger=LOG
                )

                def do_publish(connection, channel):
                    # ProducerPool ends up creating its own ConnectionPool which ends up
                    # completely invalidating this ConnectionPool. Also, a ConnectionPool for
                    # producer does not really solve any problems for us so better to create a
                    # Producer for each publish.
                    # passing exchange to Producer __init__ allows auto_declare to declare
                    # anything that's missing (especially useful for tests).
                    producer = Producer(channel, exchange=exchange)
                    kwargs = {
                        "body": payload,
                        "routing_key": routing_key,
                        "serializer": "pickle",
                        "compression": compression,
                        "content_encoding": "utf-8",
                    }

                    retry_wrapper.ensured(
                        connection=connection,
                        obj=producer,
                        to_ensure_func=producer.publish,
                        **kwargs,
                    )

                retry_wrapper.run(connection=connection, wrapped_callback=do_publish)


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
        publisher_key = "".join(urls_copy)
        publisher = self.shared_publishers.get(publisher_key, None)
        if not publisher:
            # Use original urls here to preserve order.
            publisher = PoolPublisher(urls=urls)
            self.shared_publishers[publisher_key] = publisher
        return publisher


class CUDPublisher(object):
    def __init__(self, exchange):
        urls = transport_utils.get_messaging_urls()
        self._publisher = SharedPoolPublishers().get_publisher(urls=urls)
        self._exchange = exchange

    def publish_create(self, payload):
        with Timer(key="amqp.publish.create"):
            self._publisher.publish(payload, self._exchange, CREATE_RK)

    def publish_update(self, payload):
        with Timer(key="amqp.publish.update"):
            self._publisher.publish(payload, self._exchange, UPDATE_RK)

    def publish_delete(self, payload):
        with Timer(key="amqp.publish.delete"):
            self._publisher.publish(payload, self._exchange, DELETE_RK)


class StatePublisherMixin(object):
    def __init__(self, exchange):
        urls = transport_utils.get_messaging_urls()
        self._state_publisher = SharedPoolPublishers().get_publisher(urls=urls)
        self._state_exchange = exchange

    def publish_state(self, payload, state):
        if not state:
            raise Exception("Unable to publish unassigned state.")
        with Timer(key="amqp.publish.state"):
            self._state_publisher.publish(payload, self._state_exchange, state)
