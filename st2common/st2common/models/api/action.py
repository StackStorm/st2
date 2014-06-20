from wsme import types as wstypes

from st2common import log as logging
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.action import (ActionDB, ActionExecutionDB)

__all__ = ['ActionAPI',
           'ActionExecutionAPI',
           ]


LOG = logging.getLogger(__name__)


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

    enabled = bool
    artifact_path = wstypes.text
    entry_point = wstypes.text
    """
    runner_type = wstypes.text
    parameter_names = wstypes.ArrayType(wstypes.text)
    """

    @classmethod
    def from_model(kls, model):
        action = StormBaseAPI.from_model(kls, model)
        action.enabled = bool(model.enabled)
        action.artifact_path = model.artifact_path
        action.entry_point = model.entry_point
        """
        action.parameter_names = [str(n) for n in model.parameter_names]
        """
        return action

    @classmethod
    def to_model(kls, action):
        model = StormBaseAPI.to_model(ActionDB, action)
        model.enabled = bool(action.enabled)
        model.artifact_path = str(action.artifact_path)
        model.entry_point = str(action.entry_point)

        return model


ACTIONEXEC_STATUS_INIT = 'initializing'
ACTIONEXEC_STATUS_RUNNING = 'running'
ACTIONEXEC_STATUS_COMPLETE = 'complete'
ACTIONEXEC_STATUS_ERROR = 'error'

ACTIONEXEC_STATUSES = [ACTIONEXEC_STATUS_INIT, ACTIONEXEC_STATUS_RUNNING,
                       ACTIONEXEC_STATUS_COMPLETE, ACTIONEXEC_STATUS_ERROR,
                       ]

ACTION_NAME = 'name'
ACTION_ID = 'id'


class ActionExecutionAPI(StormFoundationAPI):
    """The system entity that represents the execution of a Stack Action/Automation in
       the system.
    Attribute:
       ...
    """

    # Correct parameters...
    status = wstypes.Enum(str, *ACTIONEXEC_STATUSES)
    action = wstypes.DictType(str, str)
    runner_parameters = wstypes.DictType(str, str)
    action_parameters = wstypes.DictType(str, str)

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionExecutionAPI.from_model() Input object: %s', model)
        actionexec = StormFoundationAPI.from_model(kls, model)
        actionexec.action = dict(model.action)
        actionexec.status = str(model.status)
        actionexec.runner_parameters = dict(model.runner_parameters)
        actionexec.action_parameters = dict(model.action_parameters)
        LOG.debug('exiting ActionExecutionAPI.from_model() Result object: %s', actionexec)
        return actionexec

    @classmethod
    def to_model(kls, actionexec):
        LOG.debug('entering ActionExecutionAPI.to_model() Input object: %s', actionexec)
        model = StormFoundationAPI.to_model(ActionExecutionDB, actionexec)
        model.status = str(actionexec.status)
        model.action = actionexec.action
        model.runner_parameters = dict(actionexec.runner_parameters)
        model.action_parameters = dict(actionexec.action_parameters)
        LOG.debug('exiting ActionExecutionAPI.to_model() Result object: %s', model)
        return model
