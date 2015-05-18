# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mongoengine as me
from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase

__all__ = [
    'SensorTypeDB',
    'TriggerTypeDB',
    'TriggerDB',
    'TriggerInstanceDB',
    'ActionExecutionSpecDB',
    'RuleDB'
]


class SensorTypeDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin):
    """
    Description of a specific type of a sensor (think of it as a sensor
    template).

    Attribute:
        pack - Name of the content pack this sensor belongs to.
        artifact_uri - URI to the artifact file.
        entry_point - Full path to the sensor entry point (e.g. module.foo.ClassSensor).
        trigger_type - A list of references to the TriggerTypeDB objects exposed by this sensor.
        poll_interval - Poll interval for this sensor.
    """
    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    artifact_uri = me.StringField()
    entry_point = me.StringField()
    trigger_types = me.ListField(field=me.StringField())
    poll_interval = me.IntField()
    enabled = me.BooleanField(default=True,
                              help_text=u'Flag indicating whether the sensor is enabled.')


class TriggerTypeDB(stormbase.StormBaseDB,
                    stormbase.ContentPackResourceMixin,
                    stormbase.TagsMixin):
    """Description of a specific kind/type of a trigger. The
       (pack, name) tuple is expected uniquely identify a trigger in
       the namespace of all triggers provided by a specific trigger_source.
    Attribute:
        pack - Name of the content pack this trigger belongs to.
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """
    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    payload_schema = me.DictField()
    parameters_schema = me.DictField(default={})

    meta = {
        'indexes': stormbase.TagsMixin.get_indices()
    }


class TriggerDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin):
    """
    Attribute:
        pack - Name of the content pack this trigger belongs to.
        type - Reference to the TriggerType object.
        parameters - Trigger parameters.
    """
    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    type = me.StringField()
    parameters = me.DictField()


class TriggerInstanceDB(stormbase.StormFoundationDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the Trigger object.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """
    trigger = me.StringField()
    payload = stormbase.EscapedDictField()
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


class RuleDB(stormbase.StormFoundationDB, stormbase.TagsMixin,
             stormbase.ContentPackResourceMixin):
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
    name = me.StringField(required=True)
    ref = me.StringField(required=True)
    description = me.StringField()
    pack = me.StringField(
        required=False,
        help_text='Name of the content pack.',
        unique_with='name')
    trigger = me.StringField()
    criteria = stormbase.EscapedDictField()
    action = me.EmbeddedDocumentField(ActionExecutionSpecDB)
    enabled = me.BooleanField(required=True, default=True,
                              help_text=u'Flag indicating whether the rule is enabled.')

    meta = {
        'indexes': stormbase.TagsMixin.get_indices()
    }

# specialized access objects
sensor_type_access = MongoDBAccess(SensorTypeDB)
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)
rule_access = MongoDBAccess(RuleDB)

MODELS = [SensorTypeDB, TriggerTypeDB, TriggerDB, TriggerInstanceDB, RuleDB]
