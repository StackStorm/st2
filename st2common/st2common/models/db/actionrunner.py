from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormFoundationDB


__all__ = ['ActionRunnerDB']


LOG = logging.getLogger(__name__)


class ActionRunnerDB(StormFoundationDB):
    """
        The system entity that represents an ActionRunner environment in the system.
        This entity is used internally to manage and scale-out the StackStorm services.
        the system.

        Attributes:
    """
    pass


actionrunner_access = MongoDBAccess(ActionRunnerDB)

MODELS = [ActionRunnerDB]
