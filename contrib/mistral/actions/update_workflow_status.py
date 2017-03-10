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

from st2actions.container import service
from st2common import database_setup as setup
from st2common.constants import action as action_constants
from st2common.persistence import liveaction as persistence
from st2common.runners import base as runners
from st2common.runners import base_action as actions
from st2common.services import executions
from st2common.util import action_db as action_db_util
from st2common.util import date as date_util


class UpdateWorkflowStatusAction(actions.Action):

    def __init__(self, config, action_service=None):
        super(UpdateWorkflowStatusAction, self).__init__(
            config=config,
            action_service=action_service
        )

        setup.db_setup()

    def run(self, action_exec_id, status, result):
        self._update_action_result(action_exec_id, status, result)

    def _update_action_result(self, action_exec_id, status, result):
        liveaction_db = persistence.LiveAction.get_by_id(action_exec_id)
        if not liveaction_db:
            raise Exception('No DB model for liveaction_id: %s' % action_exec_id)

        if liveaction_db.status != action_constants.LIVEACTION_STATUS_CANCELED:
            liveaction_db.status = status

        liveaction_db.result = result

        # Action has completed, record end_timestamp
        if liveaction_db.status in action_constants.LIVEACTION_COMPLETED_STATES:
            if not liveaction_db.end_timestamp:
                liveaction_db.end_timestamp = date_util.get_datetime_utc_now()

        # update liveaction, update actionexecution and then publish update.
        updated_liveaction = persistence.LiveAction.add_or_update(liveaction_db, publish=False)
        executions.update_execution(updated_liveaction)
        persistence.LiveAction.publish_update(updated_liveaction)

        return updated_liveaction

    def _invoke_post_run(self, actionexec_db, action_db):
        self.logger.info(
            'Invoking post run for action execution %s. Action=%s; Runner=%s',
            actionexec_db.id, action_db.name, action_db.runner_type['name']
        )

        # Get an instance of the action runner.
        runnertype_db = action_db_util.get_runnertype_by_name(action_db.runner_type['name'])
        runner = runners.get_runner(runnertype_db.runner_module)

        # Configure the action runner.
        runner.container_service = service.RunnerContainerService()
        runner.action = action_db
        runner.action_name = action_db.name
        runner.action_action_exec_id = str(actionexec_db.id)
        runner.entry_point = service.RunnerContainerService.get_entry_point_abs_path(
            pack=action_db.pack, entry_point=action_db.entry_point)
        runner.context = getattr(actionexec_db, 'context', dict())
        runner.callback = getattr(actionexec_db, 'callback', dict())
        runner.libs_dir_path = service.RunnerContainerService.get_action_libs_abs_path(
            pack=action_db.pack, entry_point=action_db.entry_point)

        # Invoke the post_run method.
        runner.post_run(actionexec_db.status, actionexec_db.result)
