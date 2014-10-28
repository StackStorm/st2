import logging

from st2client.models import core


LOG = logging.getLogger(__name__)


class RunnerType(core.Resource):
    _alias = 'Runner'
    _display_name = 'Runner'
    _plural = 'RunnerTypes'
    _plural_display_name = 'Runners'


class Action(core.Resource):
    _plural = 'Actions'
    _repr_attributes = ['name', 'pack', 'enabled', 'runner_type']


class ActionExecution(core.Resource):
    _alias = 'Execution'
    _display_name = 'Action Execution'
    _plural = 'ActionExecutions'
    _plural_display_name = 'Action Executions'
