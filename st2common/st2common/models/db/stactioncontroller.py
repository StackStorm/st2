import mongoengine as me


class BaseDB(me.Document):
    """Minimal representation a model entity.
    Attribute:
        name : name of the entity.
        description : description of the entity.
        id : unique identifier for the entity. If none is provided it
        will be auto generate by the system.
    """
    name = me.StringField(required=True)
    description = me.StringField()
    id = me.ObjectIdField(primary_key=True, unique=True, required=True)


class StactionDB(Base):
    """The system entity that represents a Stack Action/Automation in
       the system.
    Attribute:
        url: url of the source
        auth_token: token used by an adapter to authenticate with the
        adapter_file_uri: uri of the adapter which will translate an event
        specific to the source to a corresponding trigger.
    """
    enabled = me.BooleanField()
    repo_path = me.StringField(required=True)
    run_type = me.StringField()
    parameter_names = ListField()
