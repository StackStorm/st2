import mongoengine as me

from st2common.models.db import MongoDBAccess

from st2common.models.db.stormbase import StormBaseDB

__all__ = ['LiveActionDB',
           'ActionRunnerDB',
           ]


class LiveActionDB(StormBaseDB):
    """The system entity that represents an Action process running in an
       ActionRunner execution environment.
    Attribute:
        pid: the OS process id for the LiveAction process.
    """
    pid = me.fields.StringField(required=True,
                          help_text=u'The PID for the action process.')


class ActionRunnerDB(StormBaseDB):
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
