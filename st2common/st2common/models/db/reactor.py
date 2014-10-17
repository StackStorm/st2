import mongoengine as me
from st2common.models.db import MongoDBAccess
from st2common.models.db.stormbase import StormBaseDB, StormFoundationDB


class TriggerTypeDB(StormBaseDB):
    """Description of a specific kind/type of a trigger. The
       (content_pack, name) tuple is expected uniquely identify a trigger in
       the namespace of all triggers provided by a specific trigger_source.
    Attribute:
        content_pack - Name of the content pack this trigger belongs to.
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """
    content_pack = me.StringField(required=True, unique_with='name')
    payload_schema = me.DictField()
    parameters_schema = me.DictField(default={})


class TriggerDB(StormBaseDB):
    type = me.DictField()
    parameters = me.DictField()


class TriggerInstanceDB(StormFoundationDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the trigger type.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """
    trigger = me.DictField()
    payload = me.DictField()
    occurrence_time = me.DateTimeField()


class ActionExecutionSpecDB(me.EmbeddedDocument):
    name = me.StringField(required=True)
    parameters = me.DictField()

    def __str__(self):
        result = []
        result.append('ActionExecutionSpecDB@')
        result.append(str(id(self)))
        result.append('(name="%s", ' % self.name)
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

    meta = {
        'indexes': [
            {'fields': ['action_execution.id']}
        ]
    }


# specialized access objects
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)
rule_access = MongoDBAccess(RuleDB)
ruleenforcement_access = MongoDBAccess(RuleEnforcementDB)

MODELS = [TriggerTypeDB, TriggerDB, TriggerInstanceDB, RuleDB,
          RuleEnforcementDB]
