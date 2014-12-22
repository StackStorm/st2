import uuid

from oslo.config import cfg
import requests

from st2actions.query.base import Querier
from st2common import log as logging

LOG = logging.getLogger(__name__)


def get_query_instance():
    return MistralResultsQuerier(str(uuid.uuid4()))


class MistralResultsQuerier(Querier):
    def __init__(self, id, *args, **kwargs):
        super(MistralResultsQuerier, Querier).__init__(*args, **kwargs)
        self._base_url = cfg.CONF.mistral.v2_base_url

    def query(self, query_context):
        exec_id = query_context.get('execution_id', None)
        if not exec_id:
            raise Exception('Mistral execution id invalid in query_context %s.'
                            % str(query_context))
        url = self._get_executions_url(exec_id)
        resp = requests.get(url)
        return resp.json()

    def _get_executions_url(self, exec_id):
        return self._base_url + 'executions/' + exec_id + '/tasks'
