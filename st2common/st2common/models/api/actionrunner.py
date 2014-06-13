from wsme import types as wstypes

from st2common.models.api.stormbase import StormBaseAPI

__all__ = ['LiveActionAPI',
           'ActionRunnerAPI',
           ]


class LiveActionAPI(StormBaseAPI):
    """The system entity that represents an Action process running in
       an ActionRunner execution environment.
    Attribute:
       pid: the OS process id for the LiveAction process. 
    """
    pid = wstypes.text

    @classmethod
    def from_model(cls, model):
        action_runner = cls()
        action_runner.id = str(model.id)


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
