from kombu import Connection
from kombu.pools import producers

CREATE_RK = 'create'
UPDATE_RK = 'update'
DELETE_RK = 'delete'


class PoolPublisher(object):
    def __init__(self, url):
        self.pool = Connection(url).Pool(10)

    def publish(self, payload, exchange, routing_key=''):
        # pickling the payload for now. Better serialization mechanism is essential.
        with self.pool.acquire(block=True) as connection:
            with producers[connection].acquire(block=True) as producer:
                producer.publish(payload, exchange=exchange, routing_key=routing_key,
                                 serializer='pickle')


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
