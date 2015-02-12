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

import json
import sys
import traceback
import datetime

from st2common import log as logging
from st2common.util import isotime
from st2common.constants.action import (ACTIONEXEC_STATUS_SUCCEEDED,
                                        ACTIONEXEC_STATUS_FAILED)
from st2common.models.db.action import ActionExecutionStateDB
from st2common.persistence.action import ActionExecutionState
from st2common.services import access
from st2common.util.action_db import (get_action_by_ref, get_runnertype_by_name)
from st2common.util.action_db import (update_actionexecution_status, get_actionexec_by_id)

from st2actions.container import actionsensor
from st2actions.container.service import RunnerContainerService
from st2actions.runners import get_runner, AsyncActionRunner
from st2actions.utils import param_utils

LOG = logging.getLogger(__name__)
DONE_STATES = [ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED]


class RunnerContainer(object):

    def __init__(self):
        LOG.info('Action RunnerContainer instantiated.')
        self._pending = []

    def dispatch(self, actionexec_db):
        action_db = get_action_by_ref(actionexec_db.action)
        if not action_db:
            raise Exception('Action %s not found in dB.' % actionexec_db.action)
        runnertype_db = get_runnertype_by_name(action_db.runner_type['name'])
        runner_type = runnertype_db.name

        LOG.info('Dispatching Action to runner \n%s',
                 json.dumps(actionexec_db.to_serializable_dict(), indent=4))
        LOG.debug('    liverunner_type: %s', runner_type)
        LOG.debug('    RunnerType: %s', runnertype_db)

        # Get runner instance.
        runner = get_runner(runnertype_db.runner_module)
        LOG.debug('Runner instance for RunnerType "%s" is: %s', runnertype_db.name, runner)

        # Invoke pre_run, run, post_run cycle.
        actionexec_db = self._do_run(runner, runnertype_db, action_db, actionexec_db)
        LOG.debug('runner do_run result: %s', actionexec_db.result)

        actionsensor.post_trigger(actionexec_db)
        actionexec_serializable = actionexec_db.to_serializable_dict()
        LOG.audit('ActionExecution complete.',
                  extra={'actionexecution': actionexec_serializable})
        LOG.info('result :\n%s.', json.dumps(actionexec_serializable.get('result', None), indent=4))

        return actionexec_db.result

    def _do_run(self, runner, runnertype_db, action_db, actionexec_db):
        resolved_entry_point = self._get_entry_point_abs_path(action_db.pack,
                                                              action_db.entry_point)
        runner.container_service = RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.action_execution_id = str(actionexec_db.id)
        runner.entry_point = resolved_entry_point
        runner.context = getattr(actionexec_db, 'context', dict())
        runner.callback = getattr(actionexec_db, 'callback', dict())
        runner.libs_dir_path = self._get_action_libs_abs_path(action_db.pack,
                                                              action_db.entry_point)
        runner.auth_token = self._create_auth_token(runner.context)

        updated_actionexec_db = None
        try:
            # Finalized parameters are resolved and then rendered. This process could
            # fail. Handle the exception and report the error correctly.
            runner_params, action_params = param_utils.get_finalized_params(
                runnertype_db.runner_parameters, action_db.parameters, actionexec_db.parameters)
            runner.runner_parameters = runner_params
            LOG.debug('Performing pre-run for runner: %s', runner)
            runner.pre_run()

            LOG.debug('Performing run for runner: %s', runner)
            (status, result, context) = runner.run(action_params)

            try:
                result = json.loads(result)
            except:
                pass

            if isinstance(runner, AsyncActionRunner) and status not in DONE_STATES:
                self._setup_async_query(actionexec_db.id, runnertype_db, context)
        except:
            LOG.exception('Failed to run action.')
            _, ex, tb = sys.exc_info()
            # mark execution as failed.
            status = ACTIONEXEC_STATUS_FAILED
            # include the error message and traceback to try and provide some hints.
            result = {'message': str(ex), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            context = None
        finally:
            updated_actionexec_db = self._update_action_execution_db(
                actionexec_db.id, status, result, context)

            LOG.debug('Updated ActionExecution after run: %s', updated_actionexec_db)

            # Always clean-up the auth_token
            try:
                self._delete_auth_token(runner.auth_token)
            except:
                LOG.warn('Unable to clean-up auth_token.')

        LOG.debug('Performing post_run for runner: %s', runner)
        runner.post_run(status, result)
        runner.container_service = None

        return updated_actionexec_db

    def _update_action_execution_db(self, actionexec_id, status, result, context):
        actionexec_db = get_actionexec_by_id(actionexec_id)

        if status in DONE_STATES:
            end_timestamp = isotime.add_utc_tz(datetime.datetime.utcnow())
        else:
            end_timestamp = None

        # Push result data and updated status to ActionExecution DB
        actionexec_db = update_actionexecution_status(status=status,
                                                      result=result,
                                                      context=context,
                                                      end_timestamp=end_timestamp,
                                                      actionexec_db=actionexec_db)
        return actionexec_db

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

    def _setup_async_query(self, actionexec_id, runnertype_db, query_context):
        query_module = getattr(runnertype_db, 'query_module', None)
        if not query_module:
            LOG.error('No query module specified for runner %s.', runnertype_db)
            return
        try:
            self._create_execution_state(actionexec_id, runnertype_db, query_context)
        except:
            LOG.exception('Unable to create action execution state db model ' +
                          'for action_execution_id %s', actionexec_id)

    def _create_execution_state(self, actionexec_id, runnertype_db, query_context):
        state_db = ActionExecutionStateDB(
            execution_id=actionexec_id,
            query_module=runnertype_db.query_module,
            query_context=query_context)
        try:
            return ActionExecutionState.add_or_update(state_db)
        except:
            LOG.exception('Unable to create execution state db for action_execution_id %s.'
                          % actionexec_id)
            return None


def get_runner_container():
    return RunnerContainer()
