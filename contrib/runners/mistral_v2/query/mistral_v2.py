import random
import time
import uuid

from mistralclient.api import base as mistralclient_base
from mistralclient.api import client as mistral
from oslo_config import cfg
import eventlet
import retrying

from st2common.query.base import Querier
from st2common.constants import action as action_constants
from st2common.exceptions import resultstracker as exceptions
from st2common import log as logging
from st2common.util import action_db as action_utils
from st2common.util import jsonify
from st2common.util.url import get_url_without_trailing_slash
from st2common.util.workflow import mistral as utils


LOG = logging.getLogger(__name__)

DONE_STATES = {
    'ERROR': action_constants.LIVEACTION_STATUS_FAILED,
    'SUCCESS': action_constants.LIVEACTION_STATUS_SUCCEEDED,
    'CANCELLED': action_constants.LIVEACTION_STATUS_CANCELED,
    'PAUSED': action_constants.LIVEACTION_STATUS_PAUSED
}

ACTIVE_STATES = {
    'RUNNING': action_constants.LIVEACTION_STATUS_RUNNING
}

CANCELED_STATES = [
    action_constants.LIVEACTION_STATUS_CANCELED,
    action_constants.LIVEACTION_STATUS_CANCELING
]

PAUSED_STATES = [
    action_constants.LIVEACTION_STATUS_PAUSED,
    action_constants.LIVEACTION_STATUS_PAUSING
]

RESUMING_STATES = [
    action_constants.LIVEACTION_STATUS_RESUMING
]


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    delete_state_object_on_error = False

    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, self).__init__(*args, **kwargs)
        self._base_url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        self._client = mistral.client(
            mistral_url=self._base_url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url,
            cacert=cfg.CONF.mistral.cacert,
            insecure=cfg.CONF.mistral.insecure)
        self._jitter = cfg.CONF.mistral.jitter_interval

    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def query(self, execution_id, query_context, last_query_time=None):
        """
        Queries mistral for workflow results using v2 APIs.
        :param execution_id: st2 execution_id (context to be used for logging/audit)
        :type execution_id: ``str``
        :param query_context: context for the query to be made to mistral. This contains mistral
                              execution id.
        :type query_context: ``object``
        :param last_query_time: Timestamp of last query.
        :type last_query_time: ``float``
        :rtype: (``str``, ``object``)
        """
        dt_last_query_time = (
            time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(last_query_time))
            if last_query_time else None
        )

        # Retrieve liveaction_db to append new result to existing result.
        liveaction_db = action_utils.get_liveaction_by_id(execution_id)

        mistral_exec_id = query_context.get('mistral', {}).get('execution_id', None)
        if not mistral_exec_id:
            raise Exception('[%s] Missing mistral workflow execution ID in query context. %s',
                            execution_id, query_context)

        try:
            wf_result = self._get_workflow_result(mistral_exec_id)

            wf_tasks_result = self._get_workflow_tasks(
                mistral_exec_id,
                last_query_time=dt_last_query_time
            )

            result = self._format_query_result(
                liveaction_db.result,
                wf_result,
                wf_tasks_result
            )
        except exceptions.ReferenceNotFoundError as exc:
            LOG.exception('[%s] Unable to find reference.', execution_id)
            return (action_constants.LIVEACTION_STATUS_FAILED, exc.message)
        except Exception:
            LOG.exception('[%s] Unable to fetch mistral workflow result and tasks. %s',
                          execution_id, query_context)
            raise

        # Retrieve liveaction_db again in case state has changed
        # while the querier get results from mistral API above.
        liveaction_db = action_utils.get_liveaction_by_id(execution_id)

        status = self._determine_execution_status(
            liveaction_db,
            result['extra']['state'],
            result['tasks']
        )

        LOG.debug('[%s] mistral workflow execution status: %s' % (execution_id, status))
        LOG.debug('[%s] mistral workflow execution result: %s' % (execution_id, result))

        return (status, result)

    def _get_workflow_result(self, exec_id):
        """
        Returns the workflow status and output. Mistral workflow status will be converted
        to st2 action status.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: (``str``, ``dict``)
        """
        try:
            jitter = random.uniform(0, self._jitter)
            eventlet.sleep(jitter)
            execution = self._client.executions.get(exec_id)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc

        result = jsonify.try_loads(execution.output) if execution.state in DONE_STATES else {}

        result['extra'] = {
            'state': execution.state,
            'state_info': execution.state_info
        }

        return result

    def _get_workflow_tasks(self, exec_id, last_query_time=None):
        """
        Returns the list of tasks for a workflow execution.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :param last_query_time: Timestamp to filter tasks
        :type last_query_time: ``str``
        :rtype: ``list``
        """
        result = []

        try:
            wf_tasks = self._client.tasks.list(workflow_execution_id=exec_id)

            if last_query_time:
                wf_tasks = [
                    t for t in wf_tasks
                    if ((t.created_at is not None and t.created_at >= last_query_time) or
                        (t.updated_at is not None and t.updated_at >= last_query_time))
                ]

            for wf_task in wf_tasks:
                result.append(self._client.tasks.get(wf_task.id))

                # Lets not blast requests but just space it out for better CPU profile
                jitter = random.uniform(0, self._jitter)
                eventlet.sleep(jitter)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc

        return [self._format_task_result(task=entry.to_dict()) for entry in result]

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

    def _format_query_result(self, current_result, new_wf_result, new_wf_tasks_result):
        result = new_wf_result

        new_wf_task_ids = [entry['id'] for entry in new_wf_tasks_result]

        old_wf_tasks_result_to_keep = [
            entry for entry in current_result.get('tasks', [])
            if entry['id'] not in new_wf_task_ids
        ]

        result['tasks'] = old_wf_tasks_result_to_keep + new_wf_tasks_result

        return result

    def _determine_execution_status(self, liveaction_db, wf_state, tasks):
        # Determine if liveaction is being canceled, paused, or resumed.
        is_action_canceled = liveaction_db.status in CANCELED_STATES
        is_action_paused = liveaction_db.status in PAUSED_STATES
        is_action_resuming = liveaction_db.status in RESUMING_STATES

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
        elif is_action_paused and active_tasks:
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif is_action_paused and not active_tasks and wf_state not in DONE_STATES:
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif not is_action_paused and active_tasks and wf_state == 'PAUSED':
            status = action_constants.LIVEACTION_STATUS_PAUSING
        elif is_action_resuming and wf_state == 'PAUSED':
            status = action_constants.LIVEACTION_STATUS_RESUMING
        elif wf_state in DONE_STATES and active_tasks:
            status = action_constants.LIVEACTION_STATUS_RUNNING
        elif wf_state in DONE_STATES and not active_tasks:
            status = DONE_STATES[wf_state]
        else:
            status = action_constants.LIVEACTION_STATUS_RUNNING

        return status
