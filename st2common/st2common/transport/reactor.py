# All Exchanges and Queues related to ActionExecution.

from kombu import Exchange, Queue
from st2common.transport import publishers

TRIGGER_XCHG = Exchange('st2.trigger',
                        type='topic')


class TriggerPublisher(publishers.CUDPublisher):

    def __init__(self, url):
        super(TriggerPublisher, self).__init__(url, TRIGGER_XCHG)


def get_trigger_queue(name, routing_key):
    return Queue(name, TRIGGER_XCHG, routing_key=routing_key)
