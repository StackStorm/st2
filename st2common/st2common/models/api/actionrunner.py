from st2common import log as logging
from st2common.models.base import BaseAPI
from st2common.models.db.actionrunner import LiveActionDB

__all__ = ['LiveActionAPI',
           'ActionRunnerAPI']


LOG = logging.getLogger(__name__)


class LiveActionAPI(BaseAPI):
    """
        The system entity that represents an Action process running in
        an ActionRunner execution environment.

        Attributes:
            id: See StormBaseAPI

            actionexecution: Dictionary that identifies the ActionExecution.
    """
    model = LiveActionDB
    schema = {
        'type': 'object',
        'parameters': {
            'id': {
                'type': 'string'
            },
            'actionexecution_id': {
                'type': 'string'
            }
        },
        'required': ['actionexecution_id'],
        'additionalProperties': False
    }

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    @classmethod
    def from_model(cls, model):
        live_action = cls._from_model(model)
        live_action.actionexecution_id = model.actionexecution_id
        return live_action

    @classmethod
    def to_model(cls, liveaction):
        model = super(cls, cls).to_model(liveaction)
        model.actionexecution_id = liveaction.actionexecution_id
        return model

    def __str__(self):
        result = []
        result.append('LiveActionAPI@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('actionexecution_id="%s", ' % self.actionexecution_id)
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


class ActionRunnerAPI(BaseAPI):
    """The system entity that represents an ActionRunner environment in the system.
       This entity is used internally to manage and scale-out the StackStorm services.
    Attribute:
       ...
    """
    schema = {
        'type': 'object',
        'parameters': {
            'id': {
                'type': 'string'
            }
        },
        'additionalProperties': False
    }
