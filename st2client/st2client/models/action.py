import logging

from st2client import models


LOG = logging.getLogger(__name__)


class ActionType(models.Resource):
    _plural = 'ActionTypes'


class Action(models.Resource):
    _plural = 'Actions'


class ActionExecution(models.Resource):
    _plural = 'ActionExecutions'
