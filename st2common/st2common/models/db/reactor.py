import mongoengine as me
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormBaseDB, StormFoundationDB
from st2common.models.db.stormbase import ContentPackResourceMixin


class SensorTypeDB(StormBaseDB, ContentPackResourceMixin):
    """
    Description of a specific type of a sensor (think of it as a sensor
    template).

    Attribute:
        content_pack - Name of the content pack this sensor belongs to.
        artifact_uri - URI to the artifact file.
        entry_point - Full path to the sensor entry point (e.g. module.foo.ClassSensor).
        trigger_type - A list of references to the TriggerTypeDB objects exposed by this sensor.
    """
    name = me.StringField(required=True)
    content_pack = me.StringField(required=True, unique_with='name')
    artifact_uri = me.StringField()
    entry_point = me.StringField()
    trigger_types = me.ListField(field=me.StringField())


class TriggerTypeDB(StormBaseDB, ContentPackResourceMixin):
    """Description of a specific kind/type of a trigger. The
       (content_pack, name) tuple is expected uniquely identify a trigger in
       the namespace of all triggers provided by a specific trigger_source.
    Attribute:
        content_pack - Name of the content pack this trigger belongs to.
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """
    name = me.StringField(required=True)
    content_pack = me.StringField(required=True, unique_with='name')
    payload_schema = me.DictField()
    parameters_schema = me.DictField(default={})


class TriggerDB(StormBaseDB, ContentPackResourceMixin):
    """
    Attribute:
        content_pack - Name of the content pack this trigger belongs to.
        type - Reference to the TriggerType object.
        parameters - Trigger parameters.
    """
    name = me.StringField(required=True)
    content_pack = me.StringField(required=True, unique_with='name')
    type = me.StringField()
    parameters = me.DictField()


class TriggerInstanceDB(StormFoundationDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the Trigger object.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """
    trigger = me.StringField()
    payload = me.DictField()
    occurrence_time = me.DateTimeField()


class ActionExecutionSpecDB(me.EmbeddedDocument):
    ref = me.StringField(required=True, unique=False)
    parameters = me.DictField()

    def __str__(self):
        result = []
        result.append('ActionExecutionSpecDB@')
        result.append(str(id(self)))
        result.append('(ref="%s", ' % self.ref)
        result.append('parameters="%s")' % self.parameters)
        return ''.join(result)


class RuleDB(StormBaseDB):
    """Specifies the action to invoke on the occurrence of a Trigger. It
    also includes the transformation to perform to match the impedance
    between the payload of a TriggerInstance and input of a action.
    Attribute:
        trigger: Trigger that trips this rule.
        criteria:
        action: Action to execute when the rule is tripped.
        status: enabled or disabled. If disabled occurrence of the trigger
        does not lead to execution of a action and vice-versa.
    """
    trigger = me.DictField()
    criteria = me.DictField()
    action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
    enabled = me.BooleanField(required=True, default=True,
                              help_text=u'Flag indicating whether the rule is enabled.')

# specialized access objects
sensor_type_access = MongoDBAccess(SensorTypeDB)
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)
rule_access = MongoDBAccess(RuleDB)

MODELS = [SensorTypeDB, TriggerTypeDB, TriggerDB, TriggerInstanceDB, RuleDB]
