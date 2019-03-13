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

import uuid

from oslo_config import cfg

from orquesta import exceptions as wf_exc
from orquesta import statuses as wf_statuses

from st2common.constants import action as ac_const
from st2common import log as logging
from st2common.models.api import notification as notify_api_models
from st2common.persistence import execution as ex_db_access
from st2common.persistence import liveaction as lv_db_access
from st2common.runners import base as runners
from st2common.services import action as ac_svc
from st2common.services import workflows as wf_svc
from st2common.util import api as api_util
from st2common.util import ujson

__all__ = [
    'OrquestaRunner',
    'get_runner',
    'get_metadata'
]


LOG = logging.getLogger(__name__)


class OrquestaRunner(runners.AsyncActionRunner):

    @staticmethod
    def get_workflow_definition(entry_point):
        with open(entry_point, 'r') as def_file:
            return def_file.read()

    def _get_notify_config(self):
        return (
            notify_api_models.NotificationsHelper.from_model(notify_model=self.liveaction.notify)
            if self.liveaction.notify
            else None
        )

    def _construct_context(self, wf_ex):
        ctx = ujson.fast_deepcopy(self.context)
        ctx['workflow_execution'] = str(wf_ex.id)

        return ctx

    def _construct_st2_context(self):
        st2_ctx = {
            'st2': {
                'action_execution_id': str(self.execution.id),
                'api_url': api_util.get_full_public_api_url(),
                'user': self.execution.context.get('user', cfg.CONF.system_user.user),
                'pack': self.execution.context.get('pack', None)
            }
        }

        if self.execution.context.get('api_user'):
            st2_ctx['st2']['api_user'] = self.execution.context.get('api_user')

        if self.execution.context:
            st2_ctx['parent'] = self.execution.context

        return st2_ctx

    def run(self, action_parameters):
        # Read workflow definition from file.
        wf_def = self.get_workflow_definition(self.entry_point)

        try:
            # Request workflow execution.
            st2_ctx = self._construct_st2_context()
            notify_cfg = self._get_notify_config()
            wf_ex_db = wf_svc.request(wf_def, self.execution, st2_ctx, notify_cfg)
        except wf_exc.WorkflowInspectionError as e:
            status = ac_const.LIVEACTION_STATUS_FAILED
            result = {'errors': e.args[1], 'output': None}
            return (status, result, self.context)
        except Exception as e:
            status = ac_const.LIVEACTION_STATUS_FAILED
            result = {'errors': [{'message': str(e)}], 'output': None}
            return (status, result, self.context)

        if wf_ex_db.status in wf_statuses.COMPLETED_STATUSES:
            status = wf_ex_db.status
            result = {'output': wf_ex_db.output or None}

            if wf_ex_db.status in wf_statuses.ABENDED_STATUSES:
                result['errors'] = wf_ex_db.errors

            for wf_ex_error in wf_ex_db.errors:
                msg = '[%s] Workflow execution completed with errors.'
                LOG.error(msg, str(self.execution.id), extra=wf_ex_error)

            return (status, result, self.context)

        # Set return values.
        status = ac_const.LIVEACTION_STATUS_RUNNING
        partial_results = {}
        ctx = self._construct_context(wf_ex_db)

        return (status, partial_results, ctx)

    @staticmethod
    def task_pauseable(ac_ex):
        wf_ex_pauseable = (
            ac_ex.runner['name'] in ac_const.WORKFLOW_RUNNER_TYPES and
            ac_ex.status == ac_const.LIVEACTION_STATUS_RUNNING
        )

        return wf_ex_pauseable

    def pause(self):
        # Pause the target workflow.
        wf_ex_db = wf_svc.request_pause(self.execution)

        # Request pause of tasks that are workflows and still running.
        for child_ex_id in self.execution.children:
            child_ex = ex_db_access.ActionExecution.get(id=child_ex_id)
            if self.task_pauseable(child_ex):
                ac_svc.request_pause(
                    lv_db_access.LiveAction.get(id=child_ex.liveaction['id']),
                    self.context.get('user', None)
                )

        if wf_ex_db.status == wf_statuses.PAUSING or ac_svc.is_children_active(self.liveaction.id):
            status = ac_const.LIVEACTION_STATUS_PAUSING
        else:
            status = ac_const.LIVEACTION_STATUS_PAUSED

        return (
            status,
            self.liveaction.result,
            self.liveaction.context
        )

    @staticmethod
    def task_resumeable(ac_ex):
        wf_ex_resumeable = (
            ac_ex.runner['name'] in ac_const.WORKFLOW_RUNNER_TYPES and
            ac_ex.status == ac_const.LIVEACTION_STATUS_PAUSED
        )

        return wf_ex_resumeable

    def resume(self):
        # Resume the target workflow.
        wf_ex_db = wf_svc.request_resume(self.execution)

        # Request resume of tasks that are workflows and still running.
        for child_ex_id in self.execution.children:
            child_ex = ex_db_access.ActionExecution.get(id=child_ex_id)
            if self.task_resumeable(child_ex):
                ac_svc.request_resume(
                    lv_db_access.LiveAction.get(id=child_ex.liveaction['id']),
                    self.context.get('user', None)
                )

        return (
            wf_ex_db.status if wf_ex_db else ac_const.LIVEACTION_STATUS_RUNNING,
            self.liveaction.result,
            self.liveaction.context
        )

    @staticmethod
    def task_cancelable(ac_ex):
        wf_ex_cancelable = (
            ac_ex.runner['name'] in ac_const.WORKFLOW_RUNNER_TYPES and
            ac_ex.status in ac_const.LIVEACTION_CANCELABLE_STATES
        )

        ac_ex_cancelable = (
            ac_ex.runner['name'] not in ac_const.WORKFLOW_RUNNER_TYPES and
            ac_ex.status in ac_const.LIVEACTION_DELAYED_STATES
        )

        return wf_ex_cancelable or ac_ex_cancelable

    def cancel(self):
        # Cancel the target workflow.
        wf_svc.request_cancellation(self.execution)

        # Request cancellation of tasks that are workflows and still running.
        for child_ex_id in self.execution.children:
            child_ex = ex_db_access.ActionExecution.get(id=child_ex_id)
            if self.task_cancelable(child_ex):
                ac_svc.request_cancellation(
                    lv_db_access.LiveAction.get(id=child_ex.liveaction['id']),
                    self.context.get('user', None)
                )

        status = (
            ac_const.LIVEACTION_STATUS_CANCELING
            if ac_svc.is_children_active(self.liveaction.id)
            else ac_const.LIVEACTION_STATUS_CANCELED
        )

        return (
            status,
            self.liveaction.result,
            self.liveaction.context
        )


def get_runner():
    return OrquestaRunner(str(uuid.uuid4()))


def get_metadata():
    return runners.get_metadata('orquesta_runner')[0]
