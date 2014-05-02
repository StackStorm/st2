import mongoengine as me


class Base(me.Document):
    """Minimal representation a model entity.
    Attribute:
        name : name of the entity.
        description : description of the entity.
        id : unique identifier for the entity. If none is provided it
        will be auto generate by the system.
    """
    name = me.StringField()
    description = me.StringField()
    id = me.ObjectIdField()
