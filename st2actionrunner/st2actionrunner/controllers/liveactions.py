from st2common import log as logging

from st2common.exceptions.db import StackStormDBObjectNotFoundError
from st2common.models.api.action import ACTIONEXEC_STATUS_RUNNING, ACTIONEXEC_STATUS_ERROR
from st2common.models.api.actionrunner import LiveActionAPI
from st2common.persistence.actionrunner import LiveAction
from st2common.util.action_db import (get_actionexec_by_id, get_action_by_dict,
                                      update_actionexecution_status, get_runnertype_by_name)
from st2common.util.actionrunner_db import (get_liveaction_by_id,
                                            get_liveactions_by_actionexec_id)

from st2actionrunner import container


LOG = logging.getLogger(__name__)


class LiveActionsController():

    def __init__(self):
        self.container = container.get_runner_container()

    def execute_action(self, liveaction_dict):
        """
            Create a new LiveAction.

            Handles requests:
                POST /liveactions/
        """
        liveaction = LiveActionAPI(**liveaction_dict)
        LOG.info('execute_action with data=%s', liveaction)

        # To launch a LiveAction we need:
        #     1. ActionExecution object
        #     2. Action object
        #     3. RunnerType object
        try:
            actionexec_db = get_actionexec_by_id(liveaction.actionexecution_id)
        except StackStormDBObjectNotFoundError as e:
            LOG.exception('Failed to find ActionExecution %s in the database.',
                          liveaction.actionexecution_id)
            # TODO: Is there a more appropriate status code?
            abort(httplib.BAD_REQUEST, str(e))

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
        except Exception as e:
            actionexec_db = update_actionexecution_status(ACTIONEXEC_STATUS_ERROR,
                                                          actionexec_db.id)
            raise

        if not result:
            raise ActionRunnerException('Failed to execute action.')

        liveaction_api = LiveActionAPI.from_model(liveaction_db)

        LOG.debug('execute_action client_result=%s', liveaction_api)
        return liveaction_api
