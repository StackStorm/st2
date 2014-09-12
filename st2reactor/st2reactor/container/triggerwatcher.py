import eventlet

from kombu.mixins import ConsumerMixin
from kombu import Connection
from oslo.config import cfg
from st2common import log as logging
from st2common.transport import reactor, publishers

LOG = logging.getLogger(__name__)


class TriggerWatcher(ConsumerMixin):

    TRIGGER_WATCH_Q = reactor.get_trigger_queue('st2.trigger.watch',
                                            routing_key='#')

    def __init__(self, create_handler, update_handler, delete_handler):
        self._handlers = {
            publishers.CREATE_RK: create_handler,
            publishers.UPDATE_RK: update_handler,
            publishers.DELETE_RK: delete_handler
        }
        self.connection = None
        self._thread = None

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[self.TRIGGER_WATCH_Q],
                         accept=['pickle'],
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        LOG.debug('process_task')
        LOG.debug('     body: %s', body)
        LOG.debug('     message.properties: %s', message.properties)
        LOG.debug('     message.delivery_info: %s', message.delivery_info)
        routing_key = message.delivery_info.get('routing_key', '')
        handler = self._handlers.get(routing_key, None)
        if not handler:
            LOG.debug('Skipping message %s as no handler was found.')
            return
        try:
            handler(body)
        except:
            LOG.exception('handling failed. Message body : %s', body)
        finally:
            message.ack()

    def start(self):
        try:
            self.connection = Connection(cfg.CONF.messaging.url)
            self._thread = eventlet.spawn(self.run)
        except:
            LOG.exception('Failed to start watcher.')
            self.connection.release()

    def stop(self):
        try:
            self._thread = eventlet.kill(self._thread)
        finally:
            self.connection.release()
