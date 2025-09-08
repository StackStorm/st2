# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import

import json
import hashlib
import sys

# TODO: Move keywords directly to hashlib.md5 call as part of dropping py3.8.
hashlib_kwargs = {} if sys.version_info[0:2] < (3, 9) else {"usedforsecurity": False}

import mongoengine as me

from st2common.models.db import MongoDBAccess
from st2common.models.db import stormbase
from st2common.fields import JSONDictEscapedFieldCompatibilityField
from st2common.constants.types import ResourceType

__all__ = [
    "TriggerTypeDB",
    "TriggerDB",
    "TriggerInstanceDB",
]


class TriggerTypeDB(
    stormbase.StormBaseDB,
    stormbase.ContentPackResourceMixin,
    stormbase.UIDFieldMixin,
    stormbase.TagsMixin,
):
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
    UID_FIELDS = ["pack", "name"]

    ref = me.StringField(required=False)
    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with="name")
    payload_schema = me.DictField()
    parameters_schema = me.DictField(default={})

    meta = {
        "indexes": (
            stormbase.ContentPackResourceMixin.get_indexes()
            + stormbase.TagsMixin.get_indexes()
            + stormbase.UIDFieldMixin.get_indexes()
        )
    }

    def __init__(self, *args, **values):
        super(TriggerTypeDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        # pylint: disable=no-member
        self.uid = self.get_uid()


class TriggerDB(
    stormbase.StormBaseDB, stormbase.ContentPackResourceMixin, stormbase.UIDFieldMixin
):
    """
    Attribute:
        name - Trigger name.
        pack - Name of the content pack this trigger belongs to.
        type - Reference to the TriggerType object.
        parameters - Trigger parameters.
    """

    RESOURCE_TYPE = ResourceType.TRIGGER
    UID_FIELDS = ["pack", "name"]

    ref = me.StringField(required=False)
    name = me.StringField(required=True)
    pack = me.StringField(required=True, unique_with="name")
    type = me.StringField()
    parameters = me.DictField()
    ref_count = me.IntField(default=0)

    meta = {
        "indexes": [
            {"fields": ["name"]},
            {"fields": ["type"]},
            {"fields": ["parameters"]},
        ]
        + stormbase.UIDFieldMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(TriggerDB, self).__init__(*args, **values)
        self.ref = self.get_reference().ref
        self.uid = self.get_uid()

    def get_uid(self):
        # Note: Trigger is uniquely identified using name + pack + parameters attributes
        # pylint: disable=no-member
        uid = super(TriggerDB, self).get_uid()

        # NOTE: We intentionally use json.dumps instead of json_encode here for backward
        # compatibility reasons.
        parameters = getattr(self, "parameters", {})
        parameters = json.dumps(parameters, sort_keys=True)
        parameters = hashlib.md5(
            parameters.encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        uid = uid + self.UID_SEPARATOR + parameters
        return uid

    def has_valid_uid(self):
        parts = self.get_uid_parts()
        # Note: We add 1 for parameters field which is not part of self.UID_FIELDS
        return len(parts) == len(self.UID_FIELDS) + 1 + 1


class TriggerInstanceDB(stormbase.StormFoundationDB):
    """An instance or occurrence of a type of Trigger.
    Attribute:
        trigger: Reference to the Trigger object.
        payload (dict): payload specific to the occurrence.
        occurrence_time (datetime): time of occurrence of the trigger.
    """

    trigger = me.StringField()
    payload = JSONDictEscapedFieldCompatibilityField()
    occurrence_time = me.DateTimeField()
    status = me.StringField(
        required=True, help_text="Processing status of TriggerInstance."
    )

    meta = {
        "indexes": [
            {"fields": ["occurrence_time"]},
            {"fields": ["trigger"]},
            {"fields": ["-occurrence_time", "trigger"]},
            {"fields": ["status"]},
        ]
    }


# specialized access objects
triggertype_access = MongoDBAccess(TriggerTypeDB)
trigger_access = MongoDBAccess(TriggerDB)
triggerinstance_access = MongoDBAccess(TriggerInstanceDB)

MODELS = [TriggerTypeDB, TriggerDB, TriggerInstanceDB]
