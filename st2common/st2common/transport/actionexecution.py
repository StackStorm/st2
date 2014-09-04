# All Exchanges and Queues related to ActionExecution.

from kombu import Exchange

CREATE_RK = 'create'

ACTIONEXECUTION_XCHG = Exchange('st2.actionexecution',
                                type='topic')
