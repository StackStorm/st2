import importlib
import json
import subprocess

from st2common import log as logging
from st2common.exceptions.actionrunner import (ActionRunnerCreateError,
                                               ActionRunnerDispatchError)
from st2common.models.api.action import (ACTIONEXEC_STATUS_COMPLETE,
                                         ACTIONEXEC_STATUS_ERROR)

from st2common.persistence.action import ActionExecution
from st2common.util.action_db import (update_actionexecution_status, get_actionexec_by_id)

from st2actionrunner.container.service import (RunnerContainerService, STDOUT, STDERR)

LOG = logging.getLogger(__name__)


class RunnerContainer():

    def __init__(self):
        LOG.info('Action RunnerContainer instantiated.')

        self._pending = []
        # self._pool = eventlet.GreenPool

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

        if runner_type == 'internaldummy':
            (exit_code, std_out, std_err) = self._handle_internaldummy_runner(
                                                      actionexec_db.runner_parameters,
                                                      actionexec_db.action_parameters)

            LOG.info('Update ActionExecution object with Action result data')
            actionexec_db.exit_code = str(exit_code)
            actionexec_db.std_out = str(json.dumps(std_out))
            actionexec_db.std_err = str(json.dumps(std_err))
            actionexec_db.status = str(ACTIONEXEC_STATUS_COMPLETE)
            actionexec_db = ActionExecution.add_or_update(actionexec_db)
            LOG.info('ActionExecution object after exit_code update: %s', actionexec_db)

            return (exit_code == 0)

        # Get runner instance.
        runner = None
        try:
            runner = self._get_runner_for_actiontype(actiontype_db)
        except ActionRunnerCreateError as e:
            raise ActionRunnerDispatchError(e.message)

        LOG.debug('Runner instance for ActionType "%s" is: %s', actiontype_db.name, runner)

        # Invoke pre_run, run, post_run cycle.
        result = self._do_run(liveaction_db.id, runner,
                              actiontype_db, action_db, actionexec_db)

        LOG.debug('runner do_run result: %s', result)

        # Update DB with status of execution
        if result:
            actionexec_status = ACTIONEXEC_STATUS_COMPLETE
        else:
            # Live Action produced error. Report in ActionExecution DB record.
            actionexec_status = ACTIONEXEC_STATUS_ERROR

        actionexec_db = update_actionexecution_status(actionexec_status,
                                                      actionexec_id=actionexec_db.id)

        LOG.audit('Live Action execution for liveaction_id="%s" resulted in '
                  'actionexecution_db="%s"', liveaction_db.id, actionexec_db)

        return result

    def _do_run(self, liveaction_id, runner, actiontype_db, action_db, actionexec_db):
        # Runner parameters should use the defaults from the ActionType object.
        # The runner parameter defaults may be overridden by values provided in
        # the Action Execution.
        runner_parameters = actiontype_db.runner_parameters
        runner_parameters.update(actionexec_db.runner_parameters)

        # Create action parameters by merging default values with dynamic values
        action_parameters = {}
        action_action_parameters = dict(action_db.parameters)
        action_parameters.update(action_action_parameters)

        actionexec_action_parameters = dict(actionexec_db.action_parameters)
        action_parameters.update(actionexec_action_parameters)

        runner.set_liveaction_id(liveaction_id)
        runner.set_container_service(RunnerContainerService(self))

        runner.set_artifact_paths(action_db.artifact_paths)
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

        # TODO: Do not flatten when DB model can store raw stream data
        # TODO: Store payload when DB model can hold payload data
        stream_map = self._get_flattened_stream_map(container_service)
        LOG.debug('Flattened stream map from container service: %s', stream_map)

        # TODO: Replace stream if statements with loop over all streams when
        #       DB model can store raw stream data
        if stream_map[STDOUT]:
            actionexec_db.std_out = str(json.dumps(stream_map[STDOUT]))
        if stream_map[STDERR]:
            actionexec_db.std_err = str(json.dumps(stream_map[STDERR]))

        if container_service._exit_code is None:
            # If the runner didn't set an exit code then the liveaction didn't complete.
            # Therefore, the liveaction produced an error.
            result = False
            actionexec_status = ACTIONEXEC_STATUS_ERROR
        else:
            # So long as the runner produced an exit code, we can assume that the
            # Live Action ran to completion.
            result = True
            actionexec_db.exit_code = str(container_service._exit_code)
            actionexec_status = ACTIONEXEC_STATUS_COMPLETE

        # Push result data and updated status to ActionExecution DB
        update_actionexecution_status(actionexec_status, actionexec_db=actionexec_db)

        return result

    def _get_flattened_stream_map(self, container_service):
        result_map = {}
        for data in container_service._output:
            if data[0] not in result_map:
                result_map[data[0]] = data[1]
            else:
                result_map[data[0]] = ''.join([result_map[data[0]], data[1]])

        return result_map

    def _handle_internaldummy_runner(self, runner_parameters, action_parameters):
        """
            ActionRunner for "internaldummy" ActionType.

            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            !!!!!!!    This is for internal scaffolding use only.    !!!!!!!
            !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        """
        LOG.info('Entering Internal Dummy Runner')

        command_list = runner_parameters['command']
        LOG.debug('    [Internal Dummy Runner] command list is: %s', command_list)

        LOG.debug('    [Internal Dummy Runner] Launching command as blocking operation.')
        process = subprocess.Popen(command_list, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True)

        command_stdout, command_stderr = process.communicate()
        command_exitcode = process.returncode

        LOG.debug('    [Internal Dummy Runner] command_stdout: %s', command_stdout)
        LOG.debug('    [Internal Dummy Runner] command_stderr: %s', command_stderr)
        LOG.debug('    [Internal Dummy Runner] command_exit: %s', command_exitcode)
        LOG.debug('    [Internal Dummy Runner] TODO: Save output to DB')

        return (command_exitcode, command_stdout, command_stderr)


def get_runner_container():
    return RunnerContainer()
