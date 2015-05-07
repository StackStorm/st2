import datetime

from kombu import Connection
from oslo.config import cfg

from st2common import log as logging
from st2common.transport import consumers, reactor
import st2reactor.container.utils as container_utils
from st2reactor.rules.engine import RulesEngine


LOG = logging.getLogger(__name__)

RULESENGINE_WORK_Q = reactor.get_trigger_instances_queue(
    name='st2.trigger_instances_dispatch.rules_engine', routing_key='#')


class TriggerInstanceDispatcher(consumers.MessageHandler):
    message_type = dict

    def __init__(self, connection, queues):
        super(TriggerInstanceDispatcher, self).__init__(connection, queues)
        self.rules_engine = RulesEngine()

    def process(self, instance):
        trigger = instance['trigger']
        payload = instance['payload']

        trigger_instance = container_utils.create_trigger_instance(
            trigger,
            payload or {},
            datetime.datetime.utcnow())

        if trigger_instance:
            self.rules_engine.handle_trigger_instance(trigger_instance)


def get_worker():
    with Connection(cfg.CONF.messaging.url) as conn:
        return TriggerInstanceDispatcher(conn, [RULESENGINE_WORK_Q])
