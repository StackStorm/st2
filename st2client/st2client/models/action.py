import logging

from st2client import models


LOG = logging.getLogger(__name__)


class ActionType(models.Resource):
    _display_name = 'Action Type'
    _plural = 'ActionTypes'
    _plural_display_name = 'Action Types'


class Action(models.Resource):
    _plural = 'Actions'


class ActionExecution(models.Resource):
    _alias = 'Execution'
    _display_name = 'Action Execution'
    _plural = 'ActionExecutions'
    _plural_display_name = 'Action Executions'
