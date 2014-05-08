import mongoengine as me
from st2common.models.db.stormbase import BaseDB
from st2common.models.db.stactioncontroller import StactionDB


class TriggerSourceDB(BaseDB):
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


class TriggerDB(BaseDB):
    """Description of a specific kind/type of a trigger. The name is expected
       uniquely identify a trigger in the namespace of all triggers provided
       by a specific trigger_source.
    Attribute:
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """
    trigger_source = me.ReferenceField(TriggerSourceDB.__name__)
    payload_info = me.ListField()


class TriggerInstanceDB(BaseDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the trigger type.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """
    trigger = me.ReferenceField(TriggerDB.__name__)
    payload = me.DictField()
    occurrence_time = me.DateTimeField()


class RuleDB(BaseDB):
    """Specifies the action to invoke on the occurrence of a Trigger. It
    also includes the transformation to perform to match the impedance
    between the payload of a TriggerInstance and input of a staction.
    Attribute:
        trigger: Trigger that trips this rule.
        staction: Staction to execute when the rule is tripped.
        data_mapping: Data mappings that describe the input of a
        staction.
        status: enabled or disabled. If disabled occurence of the trigger
        does not lead to execution of a staction and vice-versa.
    """
    trigger = me.ReferenceField(TriggerDB.__name__)
    staction = me.ReferenceField(StactionDB.__name__)
    data_mapping = me.DictField()
    status = me.StringField()


class RuleEnforcementDB(BaseDB):
    """A record of when an enabled rule was enforced.
    Attribute:
        rule (Reference): Rule that was enforced.
        trigger_instance (Reference): TriggerInstance leading to tripping of
        the rule.
        staction_execution (Reference): The StactionExecution that was
        created to record execution of a staction as part of this enforcement.
    """
    rule = me.ReferenceField(RuleDB.__name__)
    trigger_instance = me.ReferenceField(TriggerInstanceDB.__name__)
    staction_execution = me.ReferenceField(StactionDB.__name__)


class MongoDBAccess(object):
    """
    Db Object Access class. Provides general implementation which should be
    specialized for a model type.
    """
    def __init__(self, model_kls):
        self._model_kls = model_kls

    def get_by_name(self, value):
        for model_object in self._model_kls.objects(name=value):
            return model_object
        raise ValueError('{} with name "{}" does not exist.'.format(
            self._model_kls.__name__, value))

    def get_by_id(self, value):
        for model_object in self._model_kls.objects(id=value):
            return model_object
        raise ValueError('{} with id "{}" does not exist.'.format(
            self._model_kls.__name__, value))

    def get_all(self):
        return self._model_kls.objects()

    @staticmethod
    def add_or_update(model_object):
        return model_object.save()

    @staticmethod
    def delete(model_object):
        model_object.delete()

# specialized access objects
triggersource_access = MongoDBAccess(TriggerSourceDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)
rule_access = MongoDBAccess(RuleDB)
ruleenforcement_access = MongoDBAccess(RuleEnforcementDB)
