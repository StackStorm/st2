import mongoengine as me

from st2common.models.db.stormbase import BaseDB

class StactionDB(BaseDB):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        name : name of the entity.
        description : description of the entity.
        id : unique identifier for the entity. If none is provided it
        will be auto generate by the system.
        enabled: flag indicating whether this staction is enabled in the system.
        repo_path: relative path to the staction artifact. Relative to the root
                   of the repo.
        run_type: string identifying which stactionrunner is used to execute the staction.
        parameter_names: flat list of strings required as key names when running
                   the staction.
    """
    enabled = me.BooleanField()
    repo_path = me.StringField(required=True)
    run_type = me.StringField()
    parameter_names = me.ListField()
