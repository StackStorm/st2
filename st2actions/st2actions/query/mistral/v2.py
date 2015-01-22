import uuid

from oslo.config import cfg
import requests

from st2actions.query.base import Querier
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
        exec_id = query_context.get('mistral_execution_id', None)
        if not exec_id:
            raise Exception('Mistral execution id invalid in query_context %s.' %
                            str(query_context))
        url = self._get_execution_status_url(exec_id)
        resp = requests.get(url)
        try:
            status = self._get_workflow_status(resp.json())
        except:
            LOG.exception('Exception trying to get workflow status for query context: %s.' +
                          ' Will skip query.', query_context)
            raise
        url = self._get_execution_results_url(exec_id)
        resp = requests.get(url)
        LOG.debug('Mistral query results: %s' % resp.json())
        return (status, resp.json())

    def _get_execution_results_url(self, exec_id):
        return self._base_url + 'executions/' + exec_id + '/tasks'

    def _get_execution_status_url(self, exec_id):
        return self._base_url + 'executions/' + exec_id

    def _get_workflow_status(self, execution_obj):
        """
        Returns st2 status given mistral status.

        :param execution_obj: Object representing the results of API call v2/executions/${id}/tasks
        :type execution_obj: ``object``

        :rtype: ``str``
        """
        workflow_state = execution_obj.get('state', None)
        if not workflow_state:
            raise Exception('Workflow status unknown for mistral execution id %s.'
                            % execution_obj.get('id', None))
        if workflow_state in DONE_STATES:
            return DONE_STATES[workflow_state]

        return LIVEACTION_STATUS_RUNNING


def get_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))
