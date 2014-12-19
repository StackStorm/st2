import requests

from st2actions.runners.pythonrunner import Action


class WorkflowResults(Action):
    EXECUTIONS_BASE_URL = None

    def run(self, execution_id):
        resp = requests.get(self._get_executions_url(execution_id))
        return resp.json()

    def _get_executions_url(self, execution_id):
        if not WorkflowResults.EXECUTIONS_BASE_URL:
            host = self.config['host']
            api_version = self.config['api_version']
            url = host + api_version + '/executions/'
            WorkflowResults.EXECUTIONS_BASE_URL = url

        return WorkflowResults.EXECUTIONS_BASE_URL + execution_id + '/tasks'
