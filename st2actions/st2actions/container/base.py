import importlib
import sys
import traceback

from st2common import log as logging
from st2common.exceptions.actionrunner import ActionRunnerCreateError
from st2common.models.api.action import (ACTIONEXEC_STATUS_SUCCEEDED,
                                         ACTIONEXEC_STATUS_FAILED)
from st2common.services import access
from st2common.util.action_db import (get_action_by_dict, get_runnertype_by_name)
from st2common.util.action_db import (update_actionexecution_status, get_actionexec_by_id)

from st2actions.container import actionsensor
from st2actions.container.service import RunnerContainerService
from st2actions.utils import param_utils

LOG = logging.getLogger(__name__)


class RunnerContainer(object):

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
        (action_db, _) = get_action_by_dict({'name': actionexec_db.action.name})
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
        result, actionexec_db = self._do_run(runner, runnertype_db, action_db, actionexec_db)
        LOG.debug('runner do_run result: %s', result)

        actionsensor.post_trigger(actionexec_db)
        LOG.audit('ActionExecution complete. actionexec_id="%s" resulted in '
                  'actionexecution_db="%s"', actionexec_db.id, actionexec_db)

        return result

    def _do_run(self, runner, runnertype_db, action_db, actionexec_db):
        # Finalized parameters are resolved and then rendered.
        runner_params, action_params = param_utils.get_finalized_params(
            runnertype_db.runner_parameters, action_db.parameters, actionexec_db.parameters)

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
        runner.libs_dir_path = self._get_action_libs_abs_path(action_db.content_pack,
                                                              action_db.entry_point)
        runner.auth_token = self._create_auth_token(runner.context)

        try:
            LOG.debug('Performing pre-run for runner: %s', runner)
            runner.pre_run()

            LOG.debug('Performing run for runner: %s', runner)
            run_result = runner.run(action_params)
            LOG.debug('Result of run: %s', run_result)
        except:
            LOG.exception('Failed to run action.')
            _, ex, tb = sys.exc_info()
            # mark execution as failed.
            runner.container_service.report_status(ACTIONEXEC_STATUS_FAILED)
            # include the error message and traceback to try and provide some hints.
            runner.container_service.report_result(
                {'message': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))})
        finally:
            # Always clean-up the auth_token
            try:
                self._delete_auth_token(runner.auth_token)
            except:
                LOG.warn('Unable to clean-up auth_token.')

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
        actionexec_db = update_actionexecution_status(actionexec_status,
                                                      actionexec_db=actionexec_db)

        LOG.debug('Performing post_run for runner: %s', runner)
        runner.post_run()
        runner.container_service = None

        return result, actionexec_db

    def _get_entry_point_abs_path(self, pack, entry_point):
        return RunnerContainerService.get_entry_point_abs_path(pack=pack,
                                                               entry_point=entry_point)

    def _get_action_libs_abs_path(self, pack, entry_point):
        return RunnerContainerService.get_action_libs_abs_path(pack=pack,
                                                               entry_point=entry_point)

    def _create_auth_token(self, context):
        if not context:
            return None
        user = context.get('user', None)
        if not user:
            return None
        return access.create_token(user)

    def _delete_auth_token(self, auth_token):
        if auth_token:
            access.delete_token(auth_token.token)


def get_runner_container():
    return RunnerContainer()
