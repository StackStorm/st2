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
from st2common.constants.types import ResourceType

__all__ = [
    'TriggerTypeDB',
    'TriggerDB',
    'TriggerInstanceDB',
]


class TriggerTypeDB(stormbase.StormBaseDB,
                    stormbase.ContentPackResourceMixin,
                    stormbase.UIDFieldMixin,
                    stormbase.TagsMixin):
    """Description of a specific kind/type of a trigger. The
       (pack, name) tuple is expected uniquely identify a trigger in
       the namespace of all triggers provided by a specific trigger_source.
    Attribute:
        pack - Name of the content pack this trigger belongs to.
        trigger_source: Source that owns this trigger type.
        payload_info: Meta information of the expected payload.
    """

    RESOURCE_TYPE = ResourceType.TRIGGER_TYPE
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    payload_schema = me.DictField()
    parameters_schema = me.DictField(default={})

    meta = {
        'indexes': stormbase.TagsMixin.get_indices() + stormbase.UIDFieldMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(TriggerTypeDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()


class TriggerDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin,
                stormbase.UIDFieldMixin):
    """
    Attribute:
        pack - Name of the content pack this trigger belongs to.
        type - Reference to the TriggerType object.
        parameters - Trigger parameters.
    """

    RESOURCE_TYPE = ResourceType.TRIGGER_INSTANCE
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    type = me.StringField()
    parameters = me.DictField()

    def __init__(self, *args, **values):
        super(TriggerDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()


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

# specialized access objects
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)

MODELS = [TriggerTypeDB, TriggerDB, TriggerInstanceDB]
