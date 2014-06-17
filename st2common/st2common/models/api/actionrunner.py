from wsme import types as wstypes

from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)

__all__ = ['LiveActionAPI',
           'ActionRunnerAPI',
           ]


class LiveActionAPI(StormFoundationAPI):
    """The system entity that represents an Action process running in
       an ActionRunner execution environment.
    Attribute:
       pid: the OS process id for the LiveAction process. 
    """
#    action_name = wstypes.text
#    runner_parameters = wstypes.DictType(str, str)
#    action_parameters = wstypes.DictType(str, str)

    @classmethod
    def from_model(kls, model):
        live_action = StormFoundationAPI.from_model(kls, model)
#        live_action.action_name = model.action_name
#        live_action.runner_parameters = dict(model.runner_parameters)
#        live_action.action_parameters = dict(model.action_parameters)
        return live_action

    @classmethod
    def to_model(kls, model):
        liveaction = StormFoundationAPI.to_model(LiveActionDB, model)
        return liveaction


class ActionRunnerAPI(StormBaseAPI):
    """The system entity that represents an ActionRunner environment in the system.
       This entity is used internally to manage and scale-out the StackStorm services.
    Attribute:
       ...
    """
    pass

    @classmethod
    def from_model(cls, model):
        action_runner = cls()
        action_runner.id = str(model.id)
