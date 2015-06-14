from kombu import Connection
from oslo.config import cfg

from st2common import log as logging
from st2common.util import date as date_utils
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

        try:
            trigger_instance = container_utils.create_trigger_instance(
                trigger,
                payload or {},
                date_utils.get_datetime_utc_now())

            if trigger_instance:
                self.rules_engine.handle_trigger_instance(trigger_instance)
        except:
            # This could be a large message but at least in case of an exception
            # we get to see more context.
            # Beyond this point code cannot really handle the exception anyway so
            # eating up the exception.
            LOG.exception('Failed to handle trigger_instance %s.', instance)


def get_worker():
    with Connection(cfg.CONF.messaging.url) as conn:
        return TriggerInstanceDispatcher(conn, [RULESENGINE_WORK_Q])
