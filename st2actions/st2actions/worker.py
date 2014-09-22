from kombu import Connection
from kombu.mixins import ConsumerMixin
from oslo.config import cfg

from st2common import log as logging
from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import (ACTIONEXEC_STATUS_RUNNING, ACTIONEXEC_STATUS_ERROR)
from st2common.exceptions.actionrunner import (ActionRunnerPreRunError, ActionRunnerException)
from st2common.models.api.actionrunner import LiveActionAPI
from st2common.persistence.actionrunner import LiveAction
from st2common.util.action_db import (get_actionexec_by_id, get_action_by_dict,
                                      update_actionexecution_status, get_runnertype_by_name)
from st2common.transport import actionexecution, publishers

LOG = logging.getLogger(__name__)


ACTIONRUNNER_WORK_Q = actionexecution.get_queue('st2.actionrunner.work',
                                                routing_key=publishers.CREATE_RK)


class Worker(ConsumerMixin):

    def __init__(self, connection):
        self.connection = connection

    def get_consumers(self, Consumer, channel):
        consumer = Consumer(queues=[ACTIONRUNNER_WORK_Q],
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
            self.execute_action(body)
        except:
            LOG.exception('execute_action failed. Message body : %s', body)
        finally:
            message.ack()

    def execute_action(self, actionexecution):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """
        liveaction = LiveActionAPI(**{'actionexecution_id': str(actionexecution.id)})
        LOG.info('execute_action with data=%s', liveaction)

        # To launch a LiveAction we need:
        #     1. ActionExecution object
        #     2. Action object
        #     3. RunnerType object
        try:
            actionexec_db = get_actionexec_by_id(liveaction.actionexecution_id)
        except StackStormDBObjectNotFoundError:
            LOG.exception('Failed to find ActionExecution %s in the database.',
                          liveaction.actionexecution_id)
            raise

        #  Got ActionExecution object (1)
        LOG.debug('execute_action obtained ActionExecution object from database. Object is %s',
                  actionexec_db)

        (action_db, d) = get_action_by_dict(actionexec_db.action)

        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])

        # If the Action is disabled, abort the execute_action call.
        if not action_db.enabled:
            LOG.error('Unable to execute a disabled Action. Action is: %s', action_db)
            raise ActionRunnerPreRunError('Action %s is disabled cannot run.' % action_db.name)

        # Save LiveAction to DB
        liveaction_db = LiveAction.add_or_update(LiveActionAPI.to_model(liveaction))

        # Update ActionExecution status to "running"
        actionexec_db = update_actionexecution_status(ACTIONEXEC_STATUS_RUNNING,
                                                      actionexec_db.id)
        # Launch action
        LOG.audit('Launching LiveAction command with liveaction_db="%s", runnertype_db="%s", '
                  'action_db="%s", actionexec_db="%s"', liveaction_db, runnertype_db,
                  action_db, actionexec_db)

        try:
            result = self.container.dispatch(liveaction_db, runnertype_db, action_db,
                                             actionexec_db)
            LOG.debug('Runner dispatch produced result: %s', result)
        except Exception:
            actionexec_db = update_actionexecution_status(ACTIONEXEC_STATUS_ERROR,
                                                          actionexec_db.id)
            raise

        if not result:
            raise ActionRunnerException('Failed to execute action.')

        liveaction_api = LiveActionAPI.from_model(liveaction_db)

        LOG.debug('execute_action client_result=%s', liveaction_api)
        return liveaction_api


def work():
    with Connection(cfg.CONF.messaging.url) as conn:
        worker = Worker(conn)
        worker.run()
