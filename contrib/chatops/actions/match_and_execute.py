import os
import time

from st2common.runners.base_action import Action
from st2client.models.action_alias import ActionAliasMatch
from st2client.models.aliasexecution import ActionAliasExecution
from st2client.commands.action import (LIVEACTION_STATUS_REQUESTED,
                                       LIVEACTION_STATUS_SCHEDULED,
                                       LIVEACTION_STATUS_RUNNING,
                                       LIVEACTION_STATUS_CANCELING)
from st2client.client import Client


class ExecuteActionAliasAction(Action):
    def __init__(self, config=None):
        super(ExecuteActionAliasAction, self).__init__(config=config)
        api_url = os.environ.get('ST2_ACTION_API_URL', None)
        token = os.environ.get('ST2_ACTION_AUTH_TOKEN', None)
        self.client = Client(api_url=api_url, token=token)

    def run(self, text, source_channel=None, user=None):
        alias_match = ActionAliasMatch()
        alias_match.command = text
        alias, representation = self.client.managers['ActionAlias'].match(
            alias_match)

        execution = ActionAliasExecution()
        execution.name = alias.name
        execution.format = representation
        execution.command = text
        execution.source_channel = source_channel  # ?
        execution.notification_channel = None
        execution.notification_route = None
        execution.user = user

        action_exec_mgr = self.client.managers['ActionAliasExecution']

        execution = action_exec_mgr.create(execution)
        self._wait_execution_to_finish(execution.execution['id'])
        return execution.execution['id']

    def _wait_execution_to_finish(self, execution_id):
        pending_statuses = [
            LIVEACTION_STATUS_REQUESTED,
            LIVEACTION_STATUS_SCHEDULED,
            LIVEACTION_STATUS_RUNNING,
            LIVEACTION_STATUS_CANCELING
        ]
        action_exec_mgr = self.client.managers['LiveAction']
        execution = action_exec_mgr.get_by_id(execution_id)
        while execution.status in pending_statuses:
            time.sleep(1)
            execution = action_exec_mgr.get_by_id(execution_id)
