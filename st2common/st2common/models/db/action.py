import mongoengine as me

from st2common.models.db import MongoDBAccess

from st2common.models.db.stormbase import (StormFoundationDB, StormBaseDB)

__all__ = ['ActionDB',
           'ActionExecutionDB',
           ]


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

    """
    enabled = me.fields.BooleanField(required=True, default=True,
                          help_text=u'Flag indicating whether the action is enabled.')
    repo_path = me.fields.StringField(required=True,
                          help_text=u'Path to action content relative to repository base.')
    entry_point = me.fields.StringField(required=True,
                          help_text=u'Action entrypoint.')
    runner_type = me.fields.StringField(required=True,
                          help_text=u'Execution environment to use when invoking the action.')
    parameter_names = me.fields.ListField(required=True,
                          help_text=u'List of required parameter names.')
    """
    pass


class ActionExecutionDB(StormBaseDB):
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
    status = me.fields.StringField(required=True)
    action_name = me.fields.StringField(
                help_text=u'The action executed by this instance.')
    runner_parameters = me.fields.DictField(default={},
                help_text=u'The key-value pairs passed as parameters to the action runner.')
    action_parameters = me.fields.DictField(default={},
                help_text=u'The key-value pairs passed as parameters to the execution.')

    """
#    TODO: Determine whether I need to store the execution result values.
#    result_data = me.fields.EmbeddedDocumentField(ExecutionResultDB, **kwargs)
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
action_access = MongoDBAccess(ActionDB)
actionexec_access = MongoDBAccess(ActionExecutionDB)
