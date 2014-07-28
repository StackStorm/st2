import datetime
import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import (StormFoundationDB, StormBaseDB)

__all__ = ['ActionTypeDB',
           'ActionDB',
           'ActionExecutionDB']


LOG = logging.getLogger(__name__)


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


class ActionDB(StormBaseDB):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        enabled: flag indicating whether this action is enabled in the system.
        repo_path: relative path to the action artifact. Relative to the root
                   of the repo.
        run_type: string identifying which actionrunner is used to execute the action.
        parameter_names: flat list of strings required as key names when running
                   the action.
    """

    enabled = me.BooleanField(required=True, default=True,
                          help_text='Flag indicating whether the action is enabled.')
    entry_point = me.StringField(required=True,
                          help_text='Action entrypoint.')
    runner_type = me.StringField(required=True,
                          help_text='Execution environment to use when invoking the action.')
    parameters = me.DictField(default={},
                          help_text='Action parameters with optional default values.')

    def __str__(self):
        result = []
        result.append('ActionDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('name"%s", ' % self.name)
        result.append('enabled="%s", ' % self.enabled)
        result.append('entry_point="%s", ' % self.entry_point)
        result.append('runner_type="%s", ' % self.runner_type)
        result.append('parameters=%s, ' % str(self.parameters))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


class ActionExecutionDB(StormFoundationDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the
                    output and exit status code from the action.
    """

    # TODO: Can status be an enum at the Mongo layer?
    status = me.StringField(required=True,
                help_text='The current status of the ActionExecution.')
    start_timestamp = me.DateTimeField(default=datetime.datetime.now(),
                help_text='The timestamp when the ActionExecution was created.')
    action = me.DictField(required=True,
                help_text='The action executed by this instance.')
    parameters = me.DictField(default={},
                help_text='The key-value pairs passed as to the action runner & execution.')
    result = me.StringField(default='', help_text='Action defined result.')

    # TODO: Write generic str function for API and DB model base classes
    def __str__(self):
        result = []
        result.append('ActionExecutionDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id=%s, ' % self.id)
        result.append('action=%s, ' % str(self.action))
        result.append('status=%s, ' % str(self.status))
        result.append('start_timestamp=%s, ' % str(self.start_timestamp))
        result.append('parameters=%s, ' % str(self.parameters))
        result.append('result=%s, ' % self.result)
        result.append(')')
        return ''.join(result)


# specialized access objects
actiontype_access = MongoDBAccess(ActionTypeDB)
action_access = MongoDBAccess(ActionDB)
actionexec_access = MongoDBAccess(ActionExecutionDB)
