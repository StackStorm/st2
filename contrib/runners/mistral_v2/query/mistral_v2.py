import uuid

from mistralclient.api import base as mistralclient_base
from mistralclient.api import client as mistral
from oslo_config import cfg
import retrying

from st2common.query.base import Querier
from st2common.constants import action as action_constants
from st2common.exceptions import resultstracker as exceptions
from st2common import log as logging
from st2common.services import action as action_service
from st2common.util import jsonify
from st2common.util.url import get_url_without_trailing_slash
from st2common.util.workflow import mistral as utils


LOG = logging.getLogger(__name__)

DONE_STATES = {
    'ERROR': action_constants.LIVEACTION_STATUS_FAILED,
    'SUCCESS': action_constants.LIVEACTION_STATUS_SUCCEEDED,
    'CANCELLED': action_constants.LIVEACTION_STATUS_CANCELED
}

ACTIVE_STATES = {
    'RUNNING': action_constants.LIVEACTION_STATUS_RUNNING
}


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
            raise Exception('[%s] Missing mistral workflow execution ID in query context. %s',
                            execution_id, query_context)

        try:
            result = self._get_workflow_result(mistral_exec_id)
            result['tasks'] = self._get_workflow_tasks(mistral_exec_id)
        except exceptions.ReferenceNotFoundError as exc:
            LOG.exception('[%s] Unable to find reference. %s', execution_id, exc.message)
            return (action_constants.LIVEACTION_STATUS_FAILED, exc.message)
        except Exception:
            LOG.exception('[%s] Unable to fetch mistral workflow result and tasks. %s',
                          execution_id, query_context)
            raise

        status = self._determine_execution_status(
            execution_id, result['extra']['state'], result['tasks'])

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
            execution = self._client.executions.get(exec_id)
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc
        except Exception:
            raise

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
        try:
            wf_tasks = [
                self._client.tasks.get(task.id)
                for task in self._client.tasks.list(workflow_execution_id=exec_id)
            ]
        except mistralclient_base.APIException as mistral_exc:
            if 'not found' in mistral_exc.message:
                raise exceptions.ReferenceNotFoundError(mistral_exc.message)
            raise mistral_exc
        except Exception:
            raise

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
