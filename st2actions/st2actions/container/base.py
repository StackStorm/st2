import importlib

from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.models.api.action import (ACTIONEXEC_STATUS_SUCCEEDED,
                                         ACTIONEXEC_STATUS_FAILED)
from st2common.util.action_db import (get_action_by_dict, get_runnertype_by_name)
from st2common.util.action_db import (update_actionexecution_status, get_actionexec_by_id)

from st2actions.container import actionsensor
from st2actions.container.service import (RunnerContainerService)
import six


LOG = logging.getLogger(__name__)


class RunnerContainer():

    def __init__(self):
        LOG.info('Action RunnerContainer instantiated.')
        self._pending = []

    def _get_runner(self, runnertype_db):
        """
            Load the module specified by the runnertype_db.runner_module field and
            return an instance of the runner.
        """

        module_name = runnertype_db.runner_module
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

    def dispatch(self, actionexec_db):
        (action_db, _) = get_action_by_dict(actionexec_db.action)
        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])
        runner_type = runnertype_db.name

        LOG.info('Dispatching runner for Action "%s"', actionexec_db)
        LOG.debug('    liverunner_type: %s', runner_type)
        LOG.debug('    RunnerType: %s', runnertype_db)
        LOG.debug('    ActionExecution: %s', actionexec_db)

        # Get runner instance.
        runner = self._get_runner(runnertype_db)
        LOG.debug('Runner instance for RunnerType "%s" is: %s', runnertype_db.name, runner)

        # Invoke pre_run, run, post_run cycle.
        result = self._do_run(runner, runnertype_db, action_db, actionexec_db)
        LOG.debug('runner do_run result: %s', result)

        actionsensor.post_trigger(actionexec_db)
        LOG.audit('ActionExecution complete. actionexec_id="%s" resulted in '
                  'actionexecution_db="%s"', actionexec_db.id, actionexec_db)

        return result

    def _do_run(self, runner, runnertype_db, action_db, actionexec_db):
        runner_params, action_params = self.get_resolved_params(runnertype_db, action_db,
                                                                actionexec_db)
        resolved_entry_point = self._get_entry_point_abs_path(action_db.content_pack,
                                                              action_db.entry_point)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.action_execution_id = str(actionexec_db.id)
        runner.entry_point = resolved_entry_point
        runner.runner_parameters = runner_params
        runner.context = getattr(actionexec_db, 'context', dict())
        runner.callback = getattr(actionexec_db, 'callback', dict())

        LOG.debug('Performing pre-run for runner: %s', runner)
        runner.pre_run()

        LOG.debug('Performing run for runner: %s', runner)
        run_result = runner.run(action_params)
        LOG.debug('Result of run: %s', run_result)

        # Re-load Action Execution from DB:
        actionexec_db = get_actionexec_by_id(actionexec_db.id)

        # TODO: Store payload when DB model can hold payload data
        action_result = runner.container_service.get_result()
        actionexec_status = runner.container_service.get_status()
        LOG.debug('Result as reporter to container service: %s', action_result)

        if action_result is None:
            # If the runner didn't set an exit code then the action didn't complete.
            # Therefore, the action produced an error.
            result = False
            if not actionexec_status:
                actionexec_status = ACTIONEXEC_STATUS_FAILED
                runner.container_service.report_status(actionexec_status)
        else:
            # So long as the runner produced an exit code, we can assume that the
            # Live Action ran to completion.
            result = True
            actionexec_db.result = action_result
            if not actionexec_status:
                actionexec_status = ACTIONEXEC_STATUS_SUCCEEDED
                runner.container_service.report_status(actionexec_status)

        # Push result data and updated status to ActionExecution DB
        update_actionexecution_status(actionexec_status, actionexec_db=actionexec_db)

        LOG.debug('Performing post_run for runner: %s', runner)
        runner.post_run()
        runner.container_service = None

        return result

    def get_resolved_params(self, runnertype_db, action_db, actionexec_db):
        # Runner parameters should use the defaults from the RunnerType object.
        # The runner parameter defaults may be overridden by values provided in
        # the Action and ActionExecution.
        actionexec_runner_parameters, actionexec_action_parameters = RunnerContainer._split_params(
            runnertype_db, action_db, actionexec_db)
        action_parameters = dict(action_db.parameters)
        runner_params = self._get_resolved_runner_params(runnertype_db.runner_parameters,
                                                         actionexec_runner_parameters,
                                                         action_parameters)
        action_params = self._get_resolved_action_params(action_parameters,
                                                         actionexec_action_parameters)

        return runner_params, action_params

    def _get_resolved_runner_params(self, runner_parameters, actionexec_runner_parameters,
                                    action_parameters):
        # Runner parameters should use the defaults from the RunnerType object.
        # The runner parameter defaults may be overridden by values provided in
        # the Action and ActionExecution.

        # Create runner parameter by merging default values with dynamic values
        resolved_params = {k: v['default'] if 'default' in v else None
                           for k, v in six.iteritems(runner_parameters)}

        # pick overrides from action_parameters & actionexec_runner_parameters
        for param_name, param_value in six.iteritems(runner_parameters):
            # No override if param is immutable
            if param_value.get('immutable', False):
                continue
            if param_name in action_parameters and 'default' in action_parameters[param_name]:
                action_param = action_parameters[param_name]
                resolved_params[param_name] = action_param['default']
                # No further override if param is immutable
                if action_param.get('immutable', False):
                    continue
            if param_name in actionexec_runner_parameters:
                resolved_params[param_name] = actionexec_runner_parameters[param_name]

        return resolved_params

    def _get_resolved_action_params(self, action_parameters, actionexec_action_parameters):
        # Create action parameters by merging default values with dynamic values
        resolved_params = {k: v['default'] if 'default' in v else None
                           for k, v in six.iteritems(action_parameters)}

        # pick overrides from actionexec_action_parameters
        for param_name, param_value in six.iteritems(action_parameters):
            # No override if param is immutable
            if param_value.get('immutable', False):
                continue
            if param_name in actionexec_action_parameters:
                resolved_params[param_name] = actionexec_action_parameters[param_name]

        return resolved_params

    def _get_entry_point_abs_path(self, pack, entry_point):
        return RunnerContainerService.get_entry_point_abs_path(pack=pack,
                                                               entry_point=entry_point)

    @staticmethod
    def _split_params(runnertype_db, action_db, actionexec_db):
        return (
            {param: actionexec_db.parameters[param]
                for param in runnertype_db.runner_parameters if param in
                actionexec_db.parameters},

            {param: actionexec_db.parameters[param]
                for param in action_db.parameters if param in actionexec_db.parameters}
        )


def get_runner_container():
    return RunnerContainer()
