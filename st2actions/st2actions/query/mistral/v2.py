import traceback
import uuid

from mistralclient.api import client as mistral
from mistralclient.api.v2 import tasks
from mistralclient.api.v2 import executions
from oslo_config import cfg
import requests
import retrying

from st2actions.query.base import Querier
from st2common.constants import action as action_constants
from st2common import log as logging
from st2common.services import action as action_service
from st2common.util import jsonify
from st2common.util.url import get_url_without_trailing_slash
from st2common.util.workflow import mistral as utils


LOG = logging.getLogger(__name__)

DONE_STATES = {
    'ERROR': action_constants.LIVEACTION_STATUS_FAILED,
    'SUCCESS': action_constants.LIVEACTION_STATUS_SUCCEEDED
}


def get_query_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, self).__init__(*args, **kwargs)
        self._base_url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        self._client = mistral.client(
            mistral_url=self._base_url,
            username=cfg.CONF.mistral.keystone_username,
            api_key=cfg.CONF.mistral.keystone_password,
            project_name=cfg.CONF.mistral.keystone_project_name,
            auth_url=cfg.CONF.mistral.keystone_auth_url)

    @retrying.retry(
        retry_on_exception=utils.retry_on_exceptions,
        wait_exponential_multiplier=cfg.CONF.mistral.retry_exp_msec,
        wait_exponential_max=cfg.CONF.mistral.retry_exp_max_msec,
        stop_max_delay=cfg.CONF.mistral.retry_stop_max_msec)
    def query(self, execution_id, query_context):
        """
        Queries mistral for workflow results using v2 APIs.
        :param execution_id: st2 execution_id (context to be used for logging/audit)
        :type execution_id: ``str``
        :param query_context: context for the query to be made to mistral. This contains mistral
                              execution id.
        :type query_context: ``objext``
        :rtype: (``str``, ``object``)
        """
        mistral_exec_id = query_context.get('mistral', {}).get('execution_id', None)
        if not mistral_exec_id:
            LOG.exception('[%s] Missing mistral workflow execution ID in query context. %s',
                          execution_id, query_context)
            raise

        try:
            result = self._get_workflow_result(mistral_exec_id)
        except requests.exceptions.ConnectionError:
            msg = 'Unable to connect to mistral.'
            trace = traceback.format_exc(10)
            LOG.exception(msg)
            return (action_constants.LIVEACTION_STATUS_RUNNING, {'error': msg, 'traceback': trace})
        except:
            LOG.exception('[%s] Unable to fetch mistral workflow execution status and output. %s',
                          execution_id, query_context)
            raise

        try:
            result['tasks'] = self._get_workflow_tasks(mistral_exec_id)
        except requests.exceptions.ConnectionError:
            msg = 'Unable to connect to mistral.'
            trace = traceback.format_exc(10)
            LOG.exception(msg)
            return (action_constants.LIVEACTION_STATUS_RUNNING, {'error': msg, 'traceback': trace})
        except:
            LOG.exception('[%s] Unable to fetch mistral workflow tasks. %s',
                          execution_id, query_context)
            raise

        status = self._determine_execution_status(
            execution_id, result['extra']['state'], result['tasks'])

        LOG.debug('[%s] mistral workflow execution status: %s' % (execution_id, status))
        LOG.debug('[%s] mistral workflow execution result: %s' % (execution_id, result))

        return (status, result)

    def _get_execution_tasks_url(self, exec_id):
        return self._base_url + '/executions/' + exec_id + '/tasks'

    def _get_execution_url(self, exec_id):
        return self._base_url + '/executions/' + exec_id

    def _get_workflow_result(self, exec_id):
        """
        Returns the workflow status and output. Mistral workflow status will be converted
        to st2 action status.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: (``str``, ``dict``)
        """
        execution = executions.ExecutionManager(self._client).get(exec_id)

        result = jsonify.try_loads(execution.output) if execution.state in DONE_STATES else {}

        result['extra'] = {
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
        wf_tasks = tasks.TaskManager(self._client).list(workflow_execution_id=exec_id)

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

        # Identify the list of tasks that are not in completed states.
        active_tasks = [t for t in tasks if t['state'] not in DONE_STATES]

        # On cancellation, mistral workflow executions are paused so that tasks can
        # gracefully reach completion. If any task is not completed, do not mark st2
        # action execution for the workflow complete. By marking the st2 action execution
        # as running, this will keep the query for this mistral workflow execution active.
        if wf_state not in DONE_STATES and not active_tasks and is_action_canceled:
            status = action_constants.LIVEACTION_STATUS_CANCELED
        elif wf_state in DONE_STATES and active_tasks:
            status = action_constants.LIVEACTION_STATUS_RUNNING
        elif wf_state not in DONE_STATES:
            status = action_constants.LIVEACTION_STATUS_RUNNING
        else:
            status = DONE_STATES[wf_state]

        return status


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))
