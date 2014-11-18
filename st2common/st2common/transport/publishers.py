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
from kombu.pools import producers

from st2common import log as logging

CREATE_RK = 'create'
UPDATE_RK = 'update'
DELETE_RK = 'delete'

LOG = logging.getLogger(__name__)


class PoolPublisher(object):
    def __init__(self, url):
        self.pool = Connection(url).Pool(limit=10)

    def errback(self, exc, interval):
        LOG.error('Rabbitmq connection error: %s', exc.message, exc_info=False)

    def publish(self, payload, exchange, routing_key=''):
        # pickling the payload for now. Better serialization mechanism is essential.
        with self.pool.acquire(block=True) as connection:
            with producers[connection].acquire(block=True) as producer:
                try:
                    publish = connection.ensure(producer, producer.publish, errback=self.errback,
                                                max_retries=3)
                    publish(payload, exchange=exchange, routing_key=routing_key,
                            serializer='pickle')
                except Exception as e:
                    LOG.exception('Connections to rabbitmq cannot be re-established: %s',
                                  e.message, exc_info=False)


class CUDPublisher(object):
    def __init__(self, url, exchange):
        self._publisher = PoolPublisher(url)
        self._exchange = exchange

    def publish_create(self, payload):
        self._publisher.publish(payload, self._exchange, CREATE_RK)

    def publish_update(self, payload):
        self._publisher.publish(payload, self._exchange, UPDATE_RK)

    def publish_delete(self, payload):
        self._publisher.publish(payload, self._exchange, DELETE_RK)
