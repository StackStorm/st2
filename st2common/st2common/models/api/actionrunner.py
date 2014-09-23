from st2common import log as logging
from st2common.models.base import BaseAPI

__all__ = ['ActionRunnerAPI']


LOG = logging.getLogger(__name__)


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
