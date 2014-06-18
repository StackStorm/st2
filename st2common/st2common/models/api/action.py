from wsme import types as wstypes

from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.action import (ActionDB, ActionExecutionDB)

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           ]


class ActionAPI(StormBaseAPI):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        enabled: flag indicating whether this action is enabled in the system.
        repo_path: relative path to the action artifact. Relative to the root
                   of the repo.
        run_type: string identifying which actionrunner is used to execute the action.
        parameter_names: flat list of strings required as key names when running
                   the action.
    """

    """
    enabled = wstypes.bool
    repo_path = wstypes.text
    entry_point = wstypes.text
    runner_type = wstypes.text
    parameter_names = wstypes.ArrayType(wstypes.text)
    """

    @classmethod
    def from_model(kls, model):
        action = StormBaseAPI.from_model(kls, model)
        """
        action.enabled = bool(model.enabled)
        action.repo_path = model.repo_path
        action.entry_point = model.entry_point
        action.parameter_names = [str(n) for n in model.parameter_names]
        """
        return action

    @classmethod
    def to_model(kls, model):
        action = StormBaseAPI.to_model(ActionDB, model)
        return action


ACTIONEXEC_STATUS_INIT = 'initializing'
ACTIONEXEC_STATUS_RUNNING = 'running'
ACTIONEXEC_STATUS_COMPLETE = 'complete'
ACTIONEXEC_STATUS_ERROR = 'error'

ACTIONEXEC_STATUSES = [ ACTIONEXEC_STATUS_INIT, ACTIONEXEC_STATUS_RUNNING,
                        ACTIONEXEC_STATUS_COMPLETE, ACTIONEXEC_STATUS_ERROR,
                       ]

class ActionExecutionAPI(StormFoundationAPI):
    """The system entity that represents the execution of a Stack Action/Automation in
       the system.
    Attribute:
       ...
    """

    # Correct parameters...
    status = wstypes.Enum(wstypes.text, *ACTIONEXEC_STATUSES,
                            default=ACTIONEXEC_STATUS_INIT)
    action_name = wstypes.text
    runner_parameters = wstypes.DictType(wstypes.text, wstypes.text)
    action_parameters = wstypes.DictType(wstypes.text, wstypes.text)

    @classmethod
    def from_model(kls, model):
        actionexec = StormFoundationAPI.from_model(kls, model)
        actionexec.action_name = str(model.action_name)
        actionexec.status = str(ACTIONEXEC_STATUS_INIT)
        actionexec.runner_parameters = dict(model.runner_parameters)
        actionexec.action_parameters = dict(model.action_parameters)
        return actionexec

    @classmethod
    def to_model(kls, actionexec):
        model = StormFoundationAPI.to_model(ActionExecutionDB, actionexec)
        model.status = str(actionexec.status)
        model.action_name = actionexec.action_name
        model.runner_parameters = actionexec.runner_parameters
        model.action_parameters = actionexec.action_parameters
        return model
