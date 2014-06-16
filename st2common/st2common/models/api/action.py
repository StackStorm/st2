from wsme import types as wstypes

from st2common.models.api.stormbase import StormBaseAPI
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
    # TODO: debug wsme+pecan problem with "bool"
    # enabled = wstypes.bool
#    repo_path = wstypes.text
#    run_type = wstypes.text
#    parameter_names = wstypes.ArrayType(wstypes.text)

    @classmethod
    def from_model(kls, model):
        action = StormBaseAPI.from_model(kls, model)
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

class ActionExecutionAPI(StormBaseAPI):
    """The system entity that represents the execution of a Stack Action/Automation in
       the system.
    Attribute:
       ...
    """
#    status = wstypes.Enum(wstypes.text, *ACTIONEXEC_STATUSES,
#                            default=ACTIONEXEC_STATUS_INIT)
    target = wstypes.text
#    parameters = wstypes.DictType(wstypes.text, wstypes.text)

    @classmethod
    def from_model(kls, model):
        actionexec = StormBaseAPI.from_model(kls, model)
#        actionexec.status = str(ACTIONEXEC_STATUS_INIT)
        actionexec.target = str(model.target)
#        actionexec.parameters = dict(model.parameters)
        return actionexec

    @classmethod
    def to_model(kls, actionexec):
        model = StormBaseAPI.to_model(ActionExecutionDB, actionexec)
#        model.status = str(actionexec.status)
        model.target = actionexec.target
        return model
