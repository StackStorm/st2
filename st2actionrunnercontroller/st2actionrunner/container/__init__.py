import importlib

from st2common import log as logging
from st2common.exceptions.actionrunner import (ActionRunnerCreateError,
                                               ActionRunnerDispatchError)
from st2common.models.api.action import (ACTIONEXEC_STATUS_COMPLETE,
                                         ACTIONEXEC_STATUS_ERROR)

from st2common.util.action_db import (update_actionexecution_status, get_actionexec_by_id)

from st2actionrunner.container import actionsensor
from st2actionrunner.container.service import (RunnerContainerService)


LOG = logging.getLogger(__name__)


class RunnerContainer():

    def __init__(self):
        LOG.info('Action RunnerContainer instantiated.')

        self._pending = []
        actionsensor.register_trigger_type()

    def _get_runner_for_actiontype(self, actiontype_db):
        """
            Load the module specified by the actiontype_db.runner_module field and
            return an instance of the runner.
        """

        module_name = actiontype_db.runner_module
        LOG.debug('Runner loading python module: %s', module_name)
        try:
            module = importlib.import_module(module_name, package=None)
        except Exception as e:
            LOG.exception('Failed to import module %s.', module_name)
            raise ActionRunnerCreateError(e)

        LOG.debug('Instance of runner module: %s', module)

        runner = module.get_runner()
        LOG.debug('Instance of runner: %s', runner)
        return runner

    def dispatch(self, liveaction_db, actiontype_db, action_db, actionexec_db):

        runner_type = actiontype_db.name

        LOG.info('Dispatching runner for Live Action "%s"', liveaction_db)
        LOG.debug('    liverunner_type: %s', runner_type)
        LOG.debug('    ActionType: %s', actiontype_db)
        LOG.debug('    ActionExecution: %s', actionexec_db)

        # Get runner instance.
        runner = None
        try:
            runner = self._get_runner_for_actiontype(actiontype_db)
        except ActionRunnerCreateError as e:
            LOG.exception('Failed to create action of type %s.', actiontype_db.name)
            raise ActionRunnerDispatchError(e.message)

        LOG.debug('Runner instance for ActionType "%s" is: %s', actiontype_db.name, runner)

        # Invoke pre_run, run, post_run cycle.
        result = self._do_run(liveaction_db.id, runner, actiontype_db, action_db, actionexec_db)

        LOG.debug('runner do_run result: %s', result)

        # Update DB with status of execution
        if result:
            actionexec_status = ACTIONEXEC_STATUS_COMPLETE
        else:
            # Live Action produced error. Report in ActionExecution DB record.
            actionexec_status = ACTIONEXEC_STATUS_ERROR

        actionexec_db = update_actionexecution_status(actionexec_status,
                                                      actionexec_id=actionexec_db.id)
        actionsensor.post_trigger(actionexec_db)

        LOG.audit('Live Action execution for liveaction_id="%s" resulted in '
                  'actionexecution_db="%s"', liveaction_db.id, actionexec_db)

        return result

    def _do_run(self, liveaction_id, runner, actiontype_db, action_db, actionexec_db):
        # Runner parameters should use the defaults from the ActionType object.
        # The runner parameter defaults may be overridden by values provided in
        # the Action Execution.
        actionexec_runner_parameters, actionexec_action_parameters = RunnerContainer._split_params(
            actiontype_db, action_db, actionexec_db)

        runner_parameters = actiontype_db.runner_parameters
        runner_parameters.update(actionexec_runner_parameters)

        # Create action parameters by merging default values with dynamic values
        action_parameters = {}
        action_action_parameters = dict(action_db.parameters)
        action_parameters.update(action_action_parameters)
        action_parameters.update(actionexec_action_parameters)

        runner.set_liveaction_id(liveaction_id)
        runner.set_container_service(RunnerContainerService(self))

        runner.set_action_name(action_db.name)
        runner.set_entry_point(action_db.entry_point)
        runner.set_runner_parameters(runner_parameters)

        LOG.debug('Performing pre-run for runner: %s', runner)
        runner.pre_run()

        LOG.debug('Performing run for runner: %s', runner)
        run_result = runner.run(action_parameters)
        LOG.debug('Result of run: %s', run_result)

        LOG.debug('Performing post_run for runner: %s', runner)
        runner.post_run()

        container_service = runner.container_service
        runner.set_container_service(None)

        LOG.debug('Container Service after post_run: %s', container_service)

        # Re-load Action Execution from DB:
        actionexec_db = get_actionexec_by_id(actionexec_db.id)

        # TODO: Store payload when DB model can hold payload data
        action_result = container_service.get_result_json()
        LOG.debug('Result as reporter to container service: %s', action_result)

        if action_result is None:
            # If the runner didn't set an exit code then the liveaction didn't complete.
            # Therefore, the liveaction produced an error.
            result = False
            actionexec_status = ACTIONEXEC_STATUS_ERROR
        else:
            # So long as the runner produced an exit code, we can assume that the
            # Live Action ran to completion.
            result = True
            actionexec_db.result = action_result
            actionexec_status = ACTIONEXEC_STATUS_COMPLETE

        # Push result data and updated status to ActionExecution DB
        update_actionexecution_status(actionexec_status, actionexec_db=actionexec_db)

        return result

    @staticmethod
    def _split_params(actiontype_db, action_db, actionexec_db):
        return (
            {param: actionexec_db.parameters[param]
                for param in actiontype_db.runner_parameters if param in actionexec_db.parameters},

            {param: actionexec_db.parameters[param]
                for param in action_db.parameters if param in actionexec_db.parameters}
        )


def get_runner_container():
    return RunnerContainer()
