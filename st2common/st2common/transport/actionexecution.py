# All Exchanges and Queues related to ActionExecution.

from kombu import Exchange, Queue
from st2common.transport import publishers

ACTIONEXECUTION_XCHG = Exchange('st2.actionexecution',
                                type='topic')


class ActionExecutionPublisher(publishers.CUDPublisher):

    def __init__(self, url):
        super(ActionExecutionPublisher, self).__init__(url, ACTIONEXECUTION_XCHG)


def get_queue(name, routing_key):
    return Queue(name, ACTIONEXECUTION_XCHG, routing_key=routing_key)
