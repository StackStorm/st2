from wsme import types as wstypes

from st2common import log as logging
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.actionrunner import LiveActionDB

__all__ = ['LiveActionAPI',
           'ActionRunnerAPI',
           ]


LOG = logging.getLogger(__name__)


class LiveActionAPI(StormFoundationAPI):
    """The system entity that represents an Action process running in
       an ActionRunner execution environment.
    Attribute:
       pid: the OS process id for the LiveAction process. 
    """
    actionexecution_id = wstypes.text

    @classmethod
    def from_model(kls, model):
        live_action = StormFoundationAPI.from_model(kls, model)
        live_action.actionexecution_id = model.actionexecution_id
        return live_action

    @classmethod
    def to_model(kls, liveaction):
        model = StormFoundationAPI.to_model(LiveActionDB, liveaction)
        model.actionexecution_id = liveaction.actionexecution_id
        return model


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
