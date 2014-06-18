import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormFoundationDB


__all__ = ['LiveActionDB',
           'ActionRunnerDB',
           ]


LOG = logging.getLogger(__name__)


class LiveActionDB(StormFoundationDB):
    """The system entity that represents an Action process running in an
       ActionRunner execution environment.
    Attribute:
        pid: the OS process id for the LiveAction process.
    """
    action_execution_id = me.fields.StringField(required=True,
                                                help_text=u'The id of of the action_execution.')


class ActionRunnerDB(StormFoundationDB):
    """
        The system entity that represents an ActionRunner environment in the system.
        This entity is used internally to manage and scale-out the StackStorm services.
        the system.

        Attributes:
    """
    pass


class ActionExecutionResultDB(me.EmbeddedDocument):
    """
    TODO: fill-in
    Not sure if I will need this to be persisted.
    """
    exit_code = me.fields.IntField()
    std_out = me.fields.StringField()
    std_err = me.fields.StringField()


# specialized access objects
liveaction_access = MongoDBAccess(LiveActionDB)
actionrunner_access = MongoDBAccess(ActionRunnerDB)
