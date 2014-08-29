# All Exchanges and Queues related to ActionExecution.

from kombu import Exchange, Queue

CREATE_RK = 'create'

ACTIONEXECUTION_XCHG = Exchange('st2.actionexecution',
                                type='topic')

ACTIONRUNNER_WORK_Q = Queue('st2.actionrunner.work',
                            ACTIONEXECUTION_XCHG,
                            routing_key=CREATE_RK)
