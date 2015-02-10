import uuid

from oslo.config import cfg
import requests

from st2actions.query.base import Querier
from st2common.util import jsonify
from st2common import log as logging
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                                        LIVEACTION_STATUS_RUNNING)

LOG = logging.getLogger(__name__)

DONE_STATES = {'ERROR': LIVEACTION_STATUS_FAILED, 'SUCCESS': LIVEACTION_STATUS_SUCCEEDED}


def get_query_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, self).__init__(*args, **kwargs)
        self._base_url = cfg.CONF.mistral.v2_base_url

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
        exec_id = query_context.get('mistral', {}).get('execution_id', None)
        if not exec_id:
            raise Exception('Mistral execution id invalid in query_context %s.' %
                            str(query_context))

        try:
            status, output = self._get_workflow_result(exec_id)
            if output and 'tasks' in output:
                LOG.warn('Key conflict with tasks in the workflow output.')
        except:
            LOG.exception('Exception trying to get workflow status and output for '
                          'query context: %s. Will skip query.', query_context)
            raise

        result = output or {}
        result['tasks'] = self._get_workflow_tasks(exec_id)

        LOG.debug('Mistral query results: %s' % result)

        return (status, result)

    def _get_execution_tasks_url(self, exec_id):
        return self._base_url + 'executions/' + exec_id + '/tasks'

    def _get_execution_url(self, exec_id):
        return self._base_url + 'executions/' + exec_id

    def _get_workflow_result(self, exec_id):
        """
        Returns the workflow status and output. Mistral workflow status will be converted
        to st2 action status.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: (``str``, ``dict``)
        """
        url = self._get_execution_url(exec_id)
        resp = requests.get(url)
        execution = resp.json()

        workflow_state = execution.get('state', None)

        if not workflow_state:
            raise Exception('Workflow status unknown for mistral execution id %s.' % exec_id)

        if workflow_state in DONE_STATES:
            workflow_output = jsonify.try_loads(execution.get('output', {}))
            return (DONE_STATES[workflow_state], workflow_output)

        return (LIVEACTION_STATUS_RUNNING, None)

    def _get_workflow_tasks(self, exec_id):
        """
        Returns the list of tasks for a workflow execution.
        :param exec_id: Mistral execution ID
        :type exec_id: ``str``
        :rtype: ``list``
        """
        url = self._get_execution_tasks_url(exec_id)
        resp = requests.get(url)
        result = resp.json()
        tasks = result.get('tasks', [])

        result = []

        for task in tasks:
            # Format the task output
            formatted_task = self._format_task_result(task=task)
            result.append(formatted_task)

        return result

    def _format_task_result(self, task):
        """
        Format task result to follow the unified workflow result format.
        """
        result = {}

        result['id'] = task['id']
        result['name'] = task['name']
        result['execution_id'] = task.get('execution_id', None)
        result['workflow'] = task['wf_name']
        result['created_at'] = task.get('created_at', None)
        result['updated_at'] = task.get('updated_at', None)
        result['state'] = task.get('state', None)
        result['input'] = task.get('input', None)
        result['output'] = task.get('output', None)
        result['result'] = task.get('result', None)

        for attr in ['result', 'input', 'output']:
            result[attr] = jsonify.try_loads(task.get(attr, None))

        return result


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))
