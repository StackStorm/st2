import os

from st2common.runners.base_action import Action
from st2client.client import Client


class MatchAction(Action):
    def __init__(self, config=None):
        super(MatchAction, self).__init__(config=config)
        api_url = os.environ.get('ST2_ACTION_API_URL', None)
        token = os.environ.get('ST2_ACTION_AUTH_TOKEN', None)
        self.client = Client(api_url=api_url, token=token)

    def run(self, text):
        return self.client.managers['ActionAlias'].match(text)
