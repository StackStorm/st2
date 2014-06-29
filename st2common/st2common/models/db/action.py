import mongoengine as me

from st2common import log as logging
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import (StormFoundationDB, StormBaseDB)

__all__ = ['ActionDB',
           'ActionExecutionDB',
           ]


LOG = logging.getLogger(__name__)


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
                          help_text=u'Flag indicating whether the action is enabled.')
    artifact_path = me.StringField(required=True,
                          help_text=u'Path to action content relative to repository base.')
    entry_point = me.StringField(required=True,
                          help_text=u'Action entrypoint.')
    runner_type = me.StringField(required=True,
                          help_text=u'Execution environment to use when invoking the action.')
    parameter_names = me.ListField(
                          help_text=u'List of required parameter names.')

    def __str__(self):
        result = []
        result.append('ActionDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('enabled="%s", ' % self.enabled)
        result.append('artifact_path="%s", ' % self.artifact_path)
        result.append('entry_point="%s", ' % self.entry_point)
        result.append('runner_type="%s", ' % self.runner_type)
        result.append('parameter_names=%s, ' % str(self.parameter_names))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


class ActionExecutionResultDB(me.EmbeddedDocument):
    """
        Result data for a single Action execution (on a single host).
    """
    exit_code = me.StringField(default=None,
                           help_text=u'Exit code for action.')
    std_out = me.ListField(default=[],
                           help_text=u'List of stdout output strings in output order.')
    std_err = me.ListField(default=[],
                           help_text=u'List of stdout output strings in output order.')

    def __str__(self):
        result = []
        result.append('ActionExecutionResultDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('exit_code=%s' % int(self.exit_code))
        result.append('std_out=%s' % str(self.std_out))
        result.append('std_err=%s)' % str(self.std_err))
        return ''.join(result)


class ActionExecutionDB(StormFoundationDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the
                    output and exit status code from the stack action.
    """

    # TODO: Can status be an enum at the Mongo layer?
    status = me.StringField(required=True,
                help_text=u'The current status of the ActionExecution.')
    action = me.DictField(required=True,
                help_text=u'The action executed by this instance.')
    runner_parameters = me.DictField(default={},
                help_text=u'The key-value pairs passed as parameters to the action runner.')
    action_parameters = me.DictField(default={},
                help_text=u'The key-value pairs passed as parameters to the execution.')

    # TODO: Move result data to dict of embedded documents.... to support multiple action
    #       targets.
    #result_data = me.ListField( me.EmbeddedDocumentField(ActionExecutionResultDB), 
    #                           help_text=u'Output from action. Key values are hostnames.')
    #result_data = me.EmbeddedDocumentField(ActionExecutionResultDB, default=ActionExecutionResultDB(),
    #             help_text=u'Output from action. Key values are hostnames.')

    exit_code = me.StringField(default='',
                           help_text=u'Exit code for action.')
    #std_out = me.ListField(default=[],
    std_out = me.StringField(default='',
                           help_text=u'List of stdout output strings in output order.')
    #std_err = me.ListField(default=[],
    std_err = me.StringField(default='',
                           help_text=u'List of stdout output strings in output order.')

    # TODO: Write generic str function for API and DB model base classes
    def __str__(self):
        result = []
        result.append('ActionExecutionDB@')
        result.append(str(id(self)))
        result.append('(')
        result.append('id="%s", ' % self.id)
        result.append('action=%s, ' % str(self.action))
        result.append('status=%s, ' % str(self.status))
        result.append('runner_parameters=%s, ' % str(self.runner_parameters))
        result.append('action_parameters=%s, ' % str(self.action_parameters))
        result.append('exit_code=%s, ' % str(self.exit_code))
        result.append('std_out=%s, ' % str(self.std_out))
        result.append('std_err=%s, ' % str(self.std_err))
        result.append('uri="%s")' % self.uri)
        return ''.join(result)


# specialized access objects
action_access = MongoDBAccess(ActionDB)
actionexec_access = MongoDBAccess(ActionExecutionDB)
