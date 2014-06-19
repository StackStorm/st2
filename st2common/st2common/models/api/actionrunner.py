from wsme import types as wstypes

from st2common import log as logging
from st2common.models.api.stormbase import (StormFoundationAPI, StormBaseAPI)
from st2common.models.db.actionrunner import (ActionTypeDB, LiveActionDB)

__all__ = ['LiveActionAPI',
           'ActionRunnerAPI',
           ]


LOG = logging.getLogger(__name__)


class LiveActionAPI(StormFoundationAPI):
    """
        The system entity that represents an Action process running in
        an ActionRunner execution environment.

        Attributes:
            id: See StormBaseAPI

            actionexecution: Dictionary that identifies the ActionExecution.
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


class ActionTypeAPI(StormBaseAPI):
    """
        The representation of an ActionType in the system. An ActionType
        has a one-to-one mapping to a particular ActionRunner implementation.

        Attributes:
            id: See StormBaseAPI
            name: See StormBaseAPI
            description: See StormBaseAPI

            enabled: Boolean value indicating whether the runner for this type
                     is enabled.
            runner_parameter_names: The names required by the action runner to
                                    function.
            runner_module: The python module that implements the action runner
                           for this type.
    """
    enabled = bool
    runner_parameter_names = wstypes.ArrayType(str)
    runner_module = wstypes.text

    @classmethod
    def from_model(kls, model):
        LOG.debug('entering ActionTypeAPI.from_model() Input object: %s', model)

        actiontype = StormBaseAPI.from_model(kls, model)
        actiontype.enabled = bool(model.enabled)
        actiontype.runner_parameter_names = [str(v) for v in model.runner_parameter_names]
        actiontype.runner_module = str(model.runner_module)

        LOG.debug('exiting ActionTypeAPI.from_model() Result object: %s', actiontype)
        return actiontype

    @classmethod
    def to_model(kls, actiontype):
        LOG.debug('entering ActionTypeAPI.to_model() Input object: %s', actiontype)

        model = StormBaseAPI.to_model(ActionTypeDB, actiontype)
        model.enabled = bool(actiontype.enabled)
        model.runner_parameter_names = [str(v) for v in actiontype.runner_parameter_names]
        model.runner_module = str(actiontype.runner_module)
        
        LOG.debug('exiting ActionTypeAPI.to_model() Result object: %s', model)
        return model

    # TODO: Write generic str function for API and DB model base classes
    def __str__(self):
        result = 'ActionTypeAPI@' + str(id(self)) + '('
        result += 'id=%s, ' % self.id
        result += 'uri=%s, ' % self.uri
        result += 'name=%s, ' % self.name
        result += 'description=%s, ' % self.description
        result += 'enabled=%s, ' % self.enabled
        result += 'runner_parameter_names=%s, ' % str(self.runner_parameter_names)
        result += 'runner_module=%s, ' % str(self.runner_module)
        result += ')'
        return result



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
