import mongoengine as me
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormBaseDB, StormFoundationDB


class TriggerSourceDB(StormBaseDB):
    """Source of a trigger. Typically an external system or service that
    generates events which must be adapted to a trigger using the provided
    adapter.
    Attribute:
        url: url of the source
        auth_token: token used by an adapter to authenticate with the
        adapter_file_uri: uri of the adapter which will translate an event
        specific to the source to a corresponding trigger.
    """
    url = me.URLField()
    auth_token = me.StringField()
    adapter_file_uri = me.StringField()


class TriggerDB(StormBaseDB):
    """Description of a specific kind/type of a trigger. The name is expected
       uniquely identify a trigger in the namespace of all triggers provided
       by a specific trigger_source.
    Attribute:
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """
    payload_info = me.ListField()
    parameters_schema = me.DictField()


class AHTriggerDB(StormFoundationDB):
    name = me.StringField(unique_with='parameters')
    parameters = me.DictField()


class TriggerInstanceDB(StormFoundationDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the trigger type.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """
    trigger = me.ReferenceField(AHTriggerDB.__name__)
    payload = me.DictField()
    occurrence_time = me.DateTimeField()


class ActionExecutionSpecDB(me.EmbeddedDocument):
    name = me.StringField(required=True)
    parameters = me.DictField()


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
    trigger = me.ReferenceField(AHTriggerDB)
    criteria = me.DictField()
    action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
    enabled = me.BooleanField(required=True, default=True,
                              help_text=u'Flag indicating whether the rule is enabled.')


class RuleEnforcementDB(StormFoundationDB):
    """A record of when an enabled rule was enforced.
    Attribute:
        rule (Reference): Rule that was enforced.
        trigger_instance (Reference): TriggerInstance leading to tripping of
        the rule.
        action_execution (Reference): The ActionExecution that was
        created to record execution of a action as part of this enforcement.
    """
    rule = me.DictField()
    trigger_instance = me.DictField()
    action_execution = me.DictField()


# specialized access objects
triggersource_access = MongoDBAccess(TriggerSourceDB)
trigger_access = MongoDBAccess(TriggerDB)
ahtrigger_access = MongoDBAccess(AHTriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)
rule_access = MongoDBAccess(RuleDB)
ruleenforcement_access = MongoDBAccess(RuleEnforcementDB)
