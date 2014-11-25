import datetime
import st2reactor.container.utils as container_utils

from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common import log as logging
from st2common.transport.reactor import get_trigger_instances_queue
from st2common.util.greenpooldispatch import BufferedDispatcher
from st2reactor.rules.engine import RulesEngine

LOG = logging.getLogger(__name__)

RULESENGINE_WORK_Q = get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine', routing_key='#')


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.rules_engine = RulesEngine()
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
            self._dispatcher.dispatch(self._do_process_task, body['trigger'], body['payload'])
        finally:
            message.ack()

    def _do_process_task(self, trigger, payload):
        trigger_instance = container_utils.create_trigger_instance(
            trigger,
            payload or {},
            datetime.datetime.utcnow())

        if trigger_instance:
            self.rules_engine.handle_trigger_instance(trigger_instance)


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        try:
            worker.run()
        except:
            worker.shutdown()
            raise
