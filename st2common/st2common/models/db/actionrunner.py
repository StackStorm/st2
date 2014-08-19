import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormFoundationDB


__all__ = ['LiveActionDB',
           'ActionRunnerDB']


LOG = logging.getLogger(__name__)


class LiveActionDB(StormFoundationDB):
    """The system entity that represents an Action process running in an
       ActionRunner execution environment.
    Attribute:
        pid: the OS process id for the LiveAction process.
    """
    actionexecution_id = me.StringField(required=True,
                                        help_text=u'The id of of the action_execution.')


class ActionRunnerDB(StormFoundationDB):
    """
        The system entity that represents an ActionRunner environment in the system.
        This entity is used internally to manage and scale-out the StackStorm services.
        the system.

        Attributes:
    """
    pass


# specialized access objects
liveaction_access = MongoDBAccess(LiveActionDB)
actionrunner_access = MongoDBAccess(ActionRunnerDB)

MODELS = [LiveActionDB, ActionRunnerDB]
