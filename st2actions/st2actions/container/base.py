# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import json
import sys
import traceback

from oslo_config import cfg

from st2common import log as logging
from st2common.util import date as date_utils
from st2common.constants import action as action_constants
from st2common.content import utils as content_utils
from st2common.exceptions import actionrunner
from st2common.exceptions.param import ParamException
from st2common.models.db.executionstate import ActionExecutionStateDB
from st2common.models.system.action import ResolvedActionParameters
from st2common.persistence.execution import ActionExecution
from st2common.persistence.executionstate import ActionExecutionState
from st2common.services import access, executions
from st2common.util.action_db import (get_action_by_ref, get_runnertype_by_name)
from st2common.util.action_db import (update_liveaction_status, get_liveaction_by_id)
from st2common.util import param as param_utils
from st2common.util.config_loader import ContentPackConfigLoader

from st2common.runners.base import get_runner
from st2common.runners.base import AsyncActionRunner

LOG = logging.getLogger(__name__)

__all__ = [
    'RunnerContainer',
    'get_runner_container'
]


class RunnerContainer(object):

    def dispatch(self, liveaction_db):
        action_db = get_action_by_ref(liveaction_db.action)
        if not action_db:
            raise Exception('Action %s not found in DB.' % (liveaction_db.action))

        liveaction_db.context['pack'] = action_db.pack

        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])

        extra = {'liveaction_db': liveaction_db, 'runnertype_db': runnertype_db}
        LOG.info('Dispatching Action to a runner', extra=extra)

        # Get runner instance.
        runner = self._get_runner(runnertype_db, action_db, liveaction_db)

        LOG.debug('Runner instance for RunnerType "%s" is: %s', runnertype_db.name, runner)

        # Process the request.
        funcs = {
            action_constants.LIVEACTION_STATUS_REQUESTED: self._do_run,
            action_constants.LIVEACTION_STATUS_SCHEDULED: self._do_run,
            action_constants.LIVEACTION_STATUS_RUNNING: self._do_run,
            action_constants.LIVEACTION_STATUS_CANCELING: self._do_cancel,
            action_constants.LIVEACTION_STATUS_PAUSING: self._do_pause,
            action_constants.LIVEACTION_STATUS_RESUMING: self._do_resume
        }

        if liveaction_db.status not in funcs:
            raise actionrunner.ActionRunnerDispatchError(
                'Action runner is unable to dispatch the liveaction because it is '
                'in an unsupported status of "%s".' % liveaction_db.status
            )

        liveaction_db = funcs[liveaction_db.status](
            runner=runner,
            runnertype_db=runnertype_db,
            action_db=action_db,
            liveaction_db=liveaction_db
        )

        return liveaction_db.result

    def _do_run(self, runner, runnertype_db, action_db, liveaction_db):
        # Create a temporary auth token which will be available
        # for the duration of the action execution.
        runner.auth_token = self._create_auth_token(context=runner.context, action_db=action_db,
                                                    liveaction_db=liveaction_db)

        try:
            # Finalized parameters are resolved and then rendered. This process could
            # fail. Handle the exception and report the error correctly.
            try:
                runner_params, action_params = param_utils.render_final_params(
                    runnertype_db.runner_parameters, action_db.parameters, liveaction_db.parameters,
                    liveaction_db.context)
                runner.runner_parameters = runner_params
            except ParamException as e:
                raise actionrunner.ActionRunnerException(str(e))

            LOG.debug('Performing pre-run for runner: %s', runner.runner_id)
            runner.pre_run()

            # Mask secret parameters in the log context
            resolved_action_params = ResolvedActionParameters(action_db=action_db,
                                                              runner_type_db=runnertype_db,
                                                              runner_parameters=runner_params,
                                                              action_parameters=action_params)
            extra = {'runner': runner, 'parameters': resolved_action_params}
            LOG.debug('Performing run for runner: %s' % (runner.runner_id), extra=extra)
            (status, result, context) = runner.run(action_params)

            try:
                result = json.loads(result)
            except:
                pass

            action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES
            if isinstance(runner, AsyncActionRunner) and not action_completed:
                self._setup_async_query(liveaction_db.id, runnertype_db, context)
        except:
            LOG.exception('Failed to run action.')
            _, ex, tb = sys.exc_info()
            # mark execution as failed.
            status = action_constants.LIVEACTION_STATUS_FAILED
            # include the error message and traceback to try and provide some hints.
            result = {'error': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            context = None
        finally:
            # Log action completion
            extra = {'result': result, 'status': status}
            LOG.debug('Action "%s" completed.' % (action_db.name), extra=extra)

            # Update the final status of liveaction and corresponding action execution.
            liveaction_db = self._update_status(liveaction_db.id, status, result, context)

            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=status)

        LOG.debug('Performing post_run for runner: %s', runner.runner_id)
        runner.post_run(status=status, result=result)

        LOG.debug('Runner do_run result', extra={'result': liveaction_db.result})
        LOG.audit('Liveaction completed', extra={'liveaction_db': liveaction_db})

        return liveaction_db

    def _do_cancel(self, runner, runnertype_db, action_db, liveaction_db):
        try:
            extra = {'runner': runner}
            LOG.debug('Performing cancel for runner: %s', (runner.runner_id), extra=extra)
            (status, result, context) = runner.cancel()

            # Update the final status of liveaction and corresponding action execution.
            # The status is updated here because we want to keep the workflow running
            # as is if the cancel operation failed.
            liveaction_db = self._update_status(liveaction_db.id, status, result, context)
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            result = {'error': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            LOG.exception('Failed to cancel action %s.' % (liveaction_db.id), extra=result)
        finally:
            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=liveaction_db.status)

        LOG.debug('Performing post_run for runner: %s', runner.runner_id)
        result = {'error': 'Execution canceled by user.'}
        runner.post_run(status=liveaction_db.status, result=result)

        return liveaction_db

    def _do_pause(self, runner, runnertype_db, action_db, liveaction_db):
        try:
            extra = {'runner': runner}
            LOG.debug('Performing pause for runner: %s', (runner.runner_id), extra=extra)
            (status, result, context) = runner.pause()
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            status = action_constants.LIVEACTION_STATUS_FAILED
            result = {'error': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            context = liveaction_db.context
            LOG.exception('Failed to pause action %s.' % (liveaction_db.id), extra=result)
        finally:
            # Update the final status of liveaction and corresponding action execution.
            liveaction_db = self._update_status(liveaction_db.id, status, result, context)

            # Always clean-up the auth_token
            self._clean_up_auth_token(runner=runner, status=liveaction_db.status)

        return liveaction_db

    def _do_resume(self, runner, runnertype_db, action_db, liveaction_db):
        try:
            extra = {'runner': runner}
            LOG.debug('Performing resume for runner: %s', (runner.runner_id), extra=extra)

            (status, result, context) = runner.resume()

            try:
                result = json.loads(result)
            except:
                pass

            action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES

            if isinstance(runner, AsyncActionRunner) and not action_completed:
                self._setup_async_query(liveaction_db.id, runnertype_db, context)
        except:
            _, ex, tb = sys.exc_info()
            # include the error message and traceback to try and provide some hints.
            status = action_constants.LIVEACTION_STATUS_FAILED
            result = {'error': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            context = liveaction_db.context
            LOG.exception('Failed to resume action %s.' % (liveaction_db.id), extra=result)
        finally:
            # Update the final status of liveaction and corresponding action execution.
            liveaction_db = self._update_status(liveaction_db.id, status, result, context)

            # Always clean-up the auth_token
            # This method should be called in the finally block to ensure post_run is not impacted.
            self._clean_up_auth_token(runner=runner, status=liveaction_db.status)

        LOG.debug('Performing post_run for runner: %s', runner.runner_id)
        runner.post_run(status=status, result=result)

        LOG.debug('Runner do_run result', extra={'result': liveaction_db.result})
        LOG.audit('Liveaction completed', extra={'liveaction_db': liveaction_db})

        return liveaction_db

    def _clean_up_auth_token(self, runner, status):
        """
        Clean up the temporary auth token for the current action.

        Note: This method should never throw since it's called inside finally block which assumes
        it doesn't throw.
        """
        # Deletion of the runner generated auth token is delayed until the token expires.
        # Async actions such as Mistral workflows uses the auth token to launch other
        # actions in the workflow. If the auth token is deleted here, then the actions
        # in the workflow will fail with unauthorized exception.
        is_async_runner = isinstance(runner, AsyncActionRunner)
        action_completed = status in action_constants.LIVEACTION_COMPLETED_STATES

        if not is_async_runner or (is_async_runner and action_completed):
            try:
                self._delete_auth_token(runner.auth_token)
            except:
                LOG.exception('Unable to clean-up auth_token.')

            return True

        return False

    def _update_live_action_db(self, liveaction_id, status, result, context):
        """
        Update LiveActionDB object for the provided liveaction id.
        """
        liveaction_db = get_liveaction_by_id(liveaction_id)

        state_changed = (liveaction_db.status != status)

        if status in action_constants.LIVEACTION_COMPLETED_STATES:
            end_timestamp = date_utils.get_datetime_utc_now()
        else:
            end_timestamp = None

        liveaction_db = update_liveaction_status(status=status,
                                                 result=result,
                                                 context=context,
                                                 end_timestamp=end_timestamp,
                                                 liveaction_db=liveaction_db)
        return (liveaction_db, state_changed)

    def _update_status(self, liveaction_id, status, result, context):
        try:
            LOG.debug('Setting status: %s for liveaction: %s', status, liveaction_id)
            liveaction_db, state_changed = self._update_live_action_db(
                liveaction_id, status, result, context)
        except Exception as e:
            LOG.exception(
                'Cannot update liveaction '
                '(id: %s, status: %s, result: %s).' % (
                    liveaction_id, status, result)
            )
            raise e

        try:
            executions.update_execution(liveaction_db, publish=state_changed)
            extra = {'liveaction_db': liveaction_db}
            LOG.debug('Updated liveaction after run', extra=extra)
        except Exception as e:
            LOG.exception(
                'Cannot update action execution for liveaction '
                '(id: %s, status: %s, result: %s).' % (
                    liveaction_id, status, result)
            )
            raise e

        return liveaction_db

    def _get_entry_point_abs_path(self, pack, entry_point):
        return content_utils.get_entry_point_abs_path(pack=pack, entry_point=entry_point)

    def _get_action_libs_abs_path(self, pack, entry_point):
        return content_utils.get_action_libs_abs_path(pack=pack, entry_point=entry_point)

    def _get_rerun_reference(self, context):
        execution_id = context.get('re-run', {}).get('ref')
        return ActionExecution.get_by_id(execution_id) if execution_id else None

    def _get_runner(self, runnertype_db, action_db, liveaction_db):
        resolved_entry_point = self._get_entry_point_abs_path(action_db.pack,
                                                              action_db.entry_point)
        context = getattr(liveaction_db, 'context', dict())
        user = context.get('user', cfg.CONF.system_user.user)

        # Note: Right now configs are only supported by the Python runner actions
        if runnertype_db.runner_module == 'python_runner':
            LOG.debug('Loading config for pack')

            config_loader = ContentPackConfigLoader(pack_name=action_db.pack, user=user)
            config = config_loader.get_config()
        else:
            config = None

        runner = get_runner(package_name=runnertype_db.runner_package,
                            module_name=runnertype_db.runner_module,
                            config=config)

        # TODO: Pass those arguments to the constructor instead of late
        # assignment, late assignment is awful
        runner.runner_type_db = runnertype_db
        runner.action = action_db
        runner.action_name = action_db.name
        runner.liveaction = liveaction_db
        runner.liveaction_id = str(liveaction_db.id)
        runner.execution = ActionExecution.get(liveaction__id=runner.liveaction_id)
        runner.execution_id = str(runner.execution.id)
        runner.entry_point = resolved_entry_point
        runner.context = context
        runner.callback = getattr(liveaction_db, 'callback', dict())
        runner.libs_dir_path = self._get_action_libs_abs_path(action_db.pack,
                                                              action_db.entry_point)

        # For re-run, get the ActionExecutionDB in which the re-run is based on.
        rerun_ref_id = runner.context.get('re-run', {}).get('ref')
        runner.rerun_ex_ref = ActionExecution.get(id=rerun_ref_id) if rerun_ref_id else None

        return runner

    def _create_auth_token(self, context, action_db, liveaction_db):
        if not context:
            return None

        user = context.get('user', None)
        if not user:
            return None

        metadata = {
            'service': 'actions_container',
            'action_name': action_db.name,
            'live_action_id': str(liveaction_db.id)

        }

        ttl = cfg.CONF.auth.service_token_ttl
        token_db = access.create_token(username=user, ttl=ttl, metadata=metadata, service=True)
        return token_db

    def _delete_auth_token(self, auth_token):
        if auth_token:
            access.delete_token(auth_token.token)

    def _setup_async_query(self, liveaction_id, runnertype_db, query_context):
        query_module = getattr(runnertype_db, 'query_module', None)
        if not query_module:
            LOG.error('No query module specified for runner %s.', runnertype_db)
            return
        try:
            self._create_execution_state(liveaction_id, runnertype_db, query_context)
        except:
            LOG.exception('Unable to create action execution state db model ' +
                          'for liveaction_id %s', liveaction_id)

    def _create_execution_state(self, liveaction_id, runnertype_db, query_context):
        state_db = ActionExecutionStateDB(
            execution_id=liveaction_id,
            query_module=runnertype_db.query_module,
            query_context=query_context)
        try:
            return ActionExecutionState.add_or_update(state_db)
        except:
            LOG.exception('Unable to create execution state db for liveaction_id %s.'
                          % liveaction_id)
            return None


def get_runner_container():
    return RunnerContainer()
