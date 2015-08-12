import traceback
import uuid

from mistralclient.api import client as mistral
from mistralclient.api.v2 import tasks
from mistralclient.api.v2 import executions
from oslo_config import cfg
import requests

from st2actions.query.base import Querier
from st2common.util import jsonify
from st2common import log as logging
from st2common.util.url import get_url_without_trailing_slash
from st2common.constants.action import (LIVEACTION_STATUS_SUCCEEDED, LIVEACTION_STATUS_FAILED,
                                        LIVEACTION_STATUS_RUNNING)

LOG = logging.getLogger(__name__)

DONE_STATES = {'ERROR': LIVEACTION_STATUS_FAILED, 'SUCCESS': LIVEACTION_STATUS_SUCCEEDED}


def get_query_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, self).__init__(*args, **kwargs)
        self._base_url = get_url_without_trailing_slash(cfg.CONF.mistral.v2_base_url)
        self._client = mistral.client(mistral_url=self._base_url)

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
        except requests.exceptions.ConnectionError:
            msg = 'Unable to connect to mistral.'
            trace = traceback.format_exc(10)
            LOG.exception(msg)
            return (LIVEACTION_STATUS_RUNNING, {'error': msg, 'traceback': trace})
        except:
            LOG.exception('Exception trying to get workflow status and output for '
                          'query context: %s. Will skip query.', query_context)
            raise

        result = output or {}
        try:
            result['tasks'] = self._get_workflow_tasks(exec_id)
        except requests.exceptions.ConnectionError:
            msg = 'Unable to connect to mistral.'
            trace = traceback.format_exc(10)
            LOG.exception(msg)
            return (LIVEACTION_STATUS_RUNNING, {'error': msg, 'traceback': trace})
        except:
            LOG.exception('Unable to get workflow results for '
                          'query_context: %s. Will skip query.', query_context)

        LOG.debug('Mistral query results: %s' % result)

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

        if execution.state in DONE_STATES:
            return (DONE_STATES[execution.state], jsonify.try_loads(execution.output))

        return (LIVEACTION_STATUS_RUNNING, None)

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
        result = {}

        result['id'] = task['id']
        result['name'] = task['name']
        result['workflow_execution_id'] = task.get('workflow_execution_id', None)
        result['workflow_name'] = task['workflow_name']
        result['created_at'] = task.get('created_at', None)
        result['updated_at'] = task.get('updated_at', None)
        result['state'] = task.get('state', None)

        for attr in ['result', 'input', 'published']:
            result[attr] = jsonify.try_loads(task.get(attr, None))

        return result


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))
