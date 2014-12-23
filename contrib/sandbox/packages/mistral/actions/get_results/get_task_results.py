import requests

from st2actions.runners.pythonrunner import Action


class TaskResults(Action):
    TASKS_BASE_URL = None

    def run(self, task_id):
        resp = requests.get(self._get_tasks_url(task_id))
        return resp.json()

    def _get_tasks_url(self, task_id):
        if not TaskResults.TASKS_BASE_URL:
            host = self.config['host']
            api_version = self.config['api_version']
            url = host + api_version + '/tasks/'
            TaskResults.TASKS_BASE_URL = url

        return TaskResults.TASKS_BASE_URL + task_id
