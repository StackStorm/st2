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

import hashlib

import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.constants.types import ResourceType
from st2common.util import bencode

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
        name - Trigger type name.
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
        # pylint: disable=no-member
        self.uid = self.get_uid()


class TriggerDB(stormbase.StormBaseDB, stormbase.ContentPackResourceMixin,
                stormbase.UIDFieldMixin):
    """
    Attribute:
        name - Trigger name.
        pack - Name of the content pack this trigger belongs to.
        type - Reference to the TriggerType object.
        parameters - Trigger parameters.
    """

    RESOURCE_TYPE = ResourceType.TRIGGER
    UID_FIELDS = ['pack', 'name']

    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with='name')
    type = me.StringField()
    parameters = me.DictField()
    ref_count = me.IntField(default=0)

    def __init__(self, *args, **values):
        super(TriggerDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()

    def get_uid(self):
        # Note: Trigger is uniquely identified using name + pack + parameters attributes
        # pylint: disable=no-member
        uid = super(TriggerDB, self).get_uid()

        parameters = getattr(self, 'parameters', {})
        parameters = bencode.bencode(parameters)
        parameters = hashlib.md5(parameters).hexdigest()

        uid = uid + self.UID_SEPARATOR + parameters
        return uid


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
    status = me.StringField(
        required=True,
        help_text='Processing status of TriggerInstance.')

    meta = {
        'indexes': [
            {'fields': ['occurrence_time']},
            {'fields': ['trigger']},
            {'fields': ['-occurrence_time', 'trigger']},
            {'fields': ['status']}
        ]
    }


# specialized access objects
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)

MODELS = [TriggerTypeDB, TriggerDB, TriggerInstanceDB]
