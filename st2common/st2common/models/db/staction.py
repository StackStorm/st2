import mongoengine as me

from st2common.models.db import MongoDBAccess

from st2common.models.db.stormbase import BaseDB

__all__ = ['StactionDB',
           'StactionExecution',
           ]

class StactionDB(BaseDB):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        enabled: flag indicating whether this staction is enabled in the system.
        repo_path: relative path to the staction artifact. Relative to the root
                   of the repo.
        run_type: string identifying which stactionrunner is used to execute the staction.
        parameter_names: flat list of strings required as key names when running
                   the staction.
    """
    enabled = me.BooleanField(required=True, default=True, description=u'Flag indicating whether the staction is enabled.')
    repo_path = me.StringField(required=True), description=u'Path to staction content relative to repository base.')
    run_type = me.StringField(required=True, description=u'Execution environment to use when invoking the staction.')
    parameter_names = me.ListField(required=True, description=u'List of required parameter names.')

class StactionExecutionDB(BaseDB):
    """
        The databse entity that represents a Stack Action/Automation in
        the system.

        Attributes:
            status: the most recently observed status of the execution.
                    One of "starting", "running", "completed", "error".
            result: an embedded document structure that holds the 
                    output and exit status code from the stack action.
    """
    status = me.fields.StringField(required=True)
    # Initially deny any delete request that will leave a staction_execution in
    # the DB without an assocaited staction. The constraint might be relaxed to
    # "NULLIFY" if we implement the right handling in stactioncontroller.
    staction = me.fields.ReferenceField(StactionDB, reverse_delete_rule=DENY,
                description=u'The staction executed by this instance.')
    target = me.fields.StringField(required=True, default=NULL
                description=u'The target selection string.')
    parameters = me.fields.DictField(required=True, default={},
                description=u'The key-value pairs passed as parameters to the execution.')
#    TODO: Determine whether I need to store the execution result values.
#    result = me.fields.EmbeddedDocumentField(ExecutionResultDB, **kwargs)

class StactionExecutionResultDB(me.EmbeddedDocument):
    """
    TODO: fill-in
    Not sure if I will need this to be persisted.
    """
    exit_code = me.fields.IntField()
    std_out = me.fields.StringField()
    std_err = me.fields.StringField()



# specialized access objects
staction_access = MongoDBAccess(StactionDB)
