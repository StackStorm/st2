import logging

from st2client import models
from st2client.models import reactor
from st2client.models import action


LOG = logging.getLogger(__name__)


class Client(object):

    def __init__(self, endpoints):
        self.actions = models.ResourceManager(
            action.Action, endpoints['action'])
        self.executions = models.ResourceManager(
            action.ActionExecution, endpoints['action'])
        self.rules = models.ResourceManager(
            reactor.Rule, endpoints['reactor'])
        self.triggers = models.ResourceManager(
            reactor.Trigger, endpoints['reactor'], read_only=True)
