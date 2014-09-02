import json

from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg
from st2common import log as logging
from st2common.transport import actionexecution
from st2actionrunner.controllers import liveactions

LOG = logging.getLogger(__name__)


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection
        self.controller = liveactions.LiveActionsController()

    def get_consumers(self, Consumer, channel):
        return [Consumer(queues=[actionexecution.ACTIONRUNNER_WORK_Q],
                         accept=['json'],
                         callbacks=[self.process_task])]

    def process_task(self, body, message):
        # LOG.debug('process_task')
        # LOG.debug('     [%s]body: %s', type(body), body)
        # LOG.debug('     message.properties: %s', message.properties)
        # LOG.debug('     message.delivery_info: %s', message.delivery_info)
        try:
            self.controller.execute_action(json.loads(str(body)))
        except:
            LOG.exception('execute_action failed.')
        finally:
            message.ack()


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        worker.run()
