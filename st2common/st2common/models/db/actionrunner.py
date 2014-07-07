import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import (StormFoundationDB, StormBaseDB)


__all__ = ['LiveActionDB',
           'ActionRunnerDB',
           'ActionTypeDB',
           'ActionExecutionResultDB',
           ]


LOG = logging.getLogger(__name__)


class LiveActionDB(StormFoundationDB):
    """The system entity that represents an Action process running in an
       ActionRunner execution environment.
    Attribute:
        pid: the OS process id for the LiveAction process.
    """
    actionexecution_id = me.StringField(required=True,
                                        help_text=u'The id of of the action_execution.')

    def __str__(self):
        result = []
        result.append('LiveActionDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('actionexecution_id="%s", ' % self.actionexecution_id)
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


class ActionTypeDB(StormBaseDB):
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

    enabled = me.BooleanField(required=True, default=True,
                              help_text=(u'Flag indicating whether the action runner ' +
                                         u'represented by this actiontype is enabled.'))
    runner_parameters = me.DictField(required=True, default={},
                                     help_text=u'The parameter names required by the action runner. ' +
                                               u'Default values are optional.')
    runner_module = me.StringField(required=True,
                                   help_text=u'Implementation of the action runner.')

    # TODO: Write generic str function for API and DB model base classes
    def __str__(self):
        result = []
        result.append('ActionTypeDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('name="%s", ' % self.name)
        result.append('description="%s", ' % self.description)
        result.append('enabled="%s", ' % self.enabled)
        result.append('runner_module="%s", ' % str(self.runner_module))
        result.append('runner_parameters="%s", ' % str(self.runner_parameters))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


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
    exit_code = me.IntField()
    std_out = me.StringField()
    std_err = me.StringField()


# specialized access objects
liveaction_access = MongoDBAccess(LiveActionDB)
actiontype_access = MongoDBAccess(ActionTypeDB)
actionrunner_access = MongoDBAccess(ActionRunnerDB)
