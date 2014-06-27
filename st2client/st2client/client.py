import logging

from st2client import models
from st2client.models import reactor
from st2client.models import action


LOG = logging.getLogger(__name__)


class Client(object):

    def __init__(self, endpoints):
        self.managers = {}
        self.managers['Action'] = models.ResourceManager(
            action.Action, endpoints['action'])
        self.managers['ActionExecution'] = models.ResourceManager(
            action.ActionExecution, endpoints['action'])
        self.managers['Rule'] = models.ResourceManager(
            reactor.Rule, endpoints['reactor'])
        self.managers['Trigger'] = models.ResourceManager(
            reactor.Trigger, endpoints['reactor'], read_only=True)

    @property
    def actions(self):
        return self.managers['Action']

    @property
    def executions(self):
        return self.managers['ActionExecution']

    @property
    def rules(self):
        return self.managers['Rule']

    @property
    def triggers(self):
        return self.managers['Trigger']
