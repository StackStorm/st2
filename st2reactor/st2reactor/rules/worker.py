from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common import log as logging
from st2common.transport.reactor import get_trigger_queue
from st2common.util.greenpooldispatch import BufferedDispatcher

LOG = logging.getLogger(__name__)

RULESENGINE_WORK_Q = get_trigger_queue(name='st2.trigger_dispatch.rules_engine',
                                       routing_key='#')


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self._dispatcher = BufferedDispatcher()

    def shutdown(self):
        self._dispatcher.shutdown()

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[RULESENGINE_WORK_Q],
                            accept=['pickle'],
                            callbacks=[self.process_task])
        # use prefetch_count=1 for fair dispatch. This way workers that finish an item get the next
        # task and the work does not get queued behind any single large item.
        consumer.qos(prefetch_count=1)
        return [consumer]

    def process_task(self, body, message):
        # LOG.debug('process_task')
        # LOG.debug('     body: %s', body)
        # LOG.debug('     message.properties: %s', message.properties)
        # LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self._dispatcher.dispatch(self._do_process_task, body)
        finally:
            message.ack()

    def _do_process_task(self, body):
        pass


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        try:
            worker.run()
        except:
            worker.shutdown()
            raise
