import os

from st2common.runners.base_action import Action
from st2client.models.action_alias import ActionAliasMatch
from st2client.client import Client


class MatchAction(Action):
    def __init__(self, config=None):
        super(MatchAction, self).__init__(config=config)
        api_url = os.environ.get('ST2_ACTION_API_URL', None)
        token = os.environ.get('ST2_ACTION_AUTH_TOKEN', None)
        self.client = Client(api_url=api_url, token=token)

    def run(self, text):
        alias_match = ActionAliasMatch()
        alias_match.command = text
        matches = self.client.managers['ActionAlias'].match(alias_match)
        return {
            'alias': _format_match(matches[0]),
            'representation': matches[1]
        }


def _format_match(match):
    return {
        'name': match.name,
        'pack': match.pack,
        'action_ref': match.action_ref
    }
