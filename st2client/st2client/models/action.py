import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class RunnerType(core.Resource):
    _display_name = 'Runner Type'
    _plural = 'RunnerTypes'
    _plural_display_name = 'Runner Types'


class Action(core.Resource):
    _plural = 'Actions'


class ActionExecution(core.Resource):
    _alias = 'Execution'
    _display_name = 'Action Execution'
    _plural = 'ActionExecutions'
    _plural_display_name = 'Action Executions'
