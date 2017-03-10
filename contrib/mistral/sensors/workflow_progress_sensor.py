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

import datetime
import json
import uuid

from mistralclient.api import base as mistralclient_base
from mistralclient.api import client as mistral
from oslo_config import cfg

from st2common import database_setup as setup
from st2common.constants import action as action_constants
from st2common.exceptions import resultstracker as exceptions
from st2common.services import action as action_service
from st2common.util import jsonify
from st2common.util import url as url_util
from st2reactor.sensor import base as sensor


ST2_KVP_LAST_POLLED = 'last_polled'
DEFAULT_LAST_POLLED = '1900-01-01 00:00:00.0'
DT_STR_FORMAT = '%Y-%m-%d %H:%M:%S.%f'

DONE_STATES = {
    'ERROR': action_constants.LIVEACTION_STATUS_FAILED,
    'SUCCESS': action_constants.LIVEACTION_STATUS_SUCCEEDED,
    'CANCELLED': action_constants.LIVEACTION_STATUS_CANCELED
}

ACTIVE_STATES = {
    'RUNNING': action_constants.LIVEACTION_STATUS_RUNNING
}


class WorkflowStatusPoller(sensor.PollingSensor):
    """
    * self.sensor_service
        - provides utilities like
            get_logger() for writing to logs.
            dispatch() for dispatching triggers into the system.
    * self._config
        - contains configuration that was specified as
          config.yaml in the pack.
    * self._poll_interval
        - indicates the interval between two successive poll() calls.
    """

    def setup(self):
        # Setup stuff goes here. For example, you might establish connections
        # to external system once and reuse it. This is called only once by the system.
        setup.db_setup()
        self.logger = self.sensor_service.get_logger(__name__)
        self._poll_interval = 3
        self._base_url = url_util.get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        self._client = mistral.client(
            mistral_url=self._base_url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url,
            cacert=cfg.CONF.mistral.cacert,
            insecure=cfg.CONF.mistral.insecure)

    def poll(self):
        # This is where the crux of the sensor work goes.
        # This is called every self._poll_interval.

        str_last_polled = self.sensor_service.get_value(ST2_KVP_LAST_POLLED) or DEFAULT_LAST_POLLED

        dt_timestamp = datetime.datetime.utcnow()

        updated_workflows = self._client.executions.list(updated_at='gte:%s' % str_last_polled)

        for workflow in updated_workflows:
            try:
                result = self._get_workflow_result(workflow.id)
                result['tasks'] = self._get_workflow_tasks(workflow.id)

                status = self._determine_execution_status(
                    result['extra']['params']['env']['st2_liveaction_id'],
                    result['extra']['state'],
                    result['tasks']
                )

                payload = {
                    'id': result['extra']['params']['env']['st2_liveaction_id'],
                    'status': status,
                    'result': result
                }

                self.sensor_service.dispatch(
                    trigger='mistral.workflow.status.update',
                    payload=payload,
                    trace_tag=uuid.uuid4().hex
                )
            except Exception:
                self.logger.exception('[%s] Unable to dispatch workflow result.', workflow.id)
                continue

        self.sensor_service.set_value(
            name=ST2_KVP_LAST_POLLED,
            value=str(dt_timestamp)
        )

    def cleanup(self):
        # This is called when the st2 system goes down. You can perform cleanup operations like
        # closing the connections to external system here.
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass

    def _get_workflow_result(self, exec_id):
        """
        Returns the workflow status and output. Mistral workflow status will be converted
        to st2 action status.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: (``str``, ``dict``)
        """
        try:
            execution = self._client.executions.get(exec_id)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc

        params = json.loads(execution.params)

        result = jsonify.try_loads(execution.output) if execution.state in DONE_STATES else {}

        result['extra'] = {
            'params': params,
            'state': execution.state,
            'state_info': execution.state_info
        }

        return result

    def _get_workflow_tasks(self, exec_id):
        """
        Returns the list of tasks for a workflow execution.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: ``list``
        """
        wf_tasks = []

        try:
            for task in self._client.tasks.list(workflow_execution_id=exec_id):
                wf_tasks.append(self._client.tasks.get(task.id))
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc

        return [self._format_task_result(task=wf_task.to_dict()) for wf_task in wf_tasks]

    def _format_task_result(self, task):
        """
        Format task result to follow the unified workflow result format.
        """
        result = {
            'id': task['id'],
            'name': task['name'],
            'workflow_execution_id': task.get('workflow_execution_id', None),
            'workflow_name': task['workflow_name'],
            'created_at': task.get('created_at', None),
            'updated_at': task.get('updated_at', None),
            'state': task.get('state', None),
            'state_info': task.get('state_info', None)
        }

        for attr in ['result', 'input', 'published']:
            result[attr] = jsonify.try_loads(task.get(attr, None))

        return result

    def _determine_execution_status(self, execution_id, wf_state, tasks):
        # Get the liveaction object to compare state.
        is_action_canceled = action_service.is_action_canceled_or_canceling(execution_id)

        # Identify the list of tasks that are not still running.
        active_tasks = [t for t in tasks if t['state'] in ACTIVE_STATES]

        # Keep the execution in running state if there are active tasks.
        # In certain use cases, Mistral sets the workflow state to
        # completion prior to task completion.
        if is_action_canceled and active_tasks:
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif is_action_canceled and not active_tasks and wf_state not in DONE_STATES:
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif not is_action_canceled and active_tasks and wf_state == 'CANCELLED':
            status = action_constants.LIVEACTION_STATUS_CANCELING
        elif wf_state in DONE_STATES and active_tasks:
            status = action_constants.LIVEACTION_STATUS_RUNNING
        elif wf_state in DONE_STATES and not active_tasks:
            status = DONE_STATES[wf_state]
        else:
            status = action_constants.LIVEACTION_STATUS_RUNNING

        return status
