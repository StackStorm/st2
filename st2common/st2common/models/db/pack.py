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
    'PackDB',
    'ConfigSchemaDB',
    'ConfigDB'
]


class PackDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin):
    """
    System entity which represents a pack.
    """

    RESOURCE_TYPE = ResourceType.PACK
    UID_FIELDS = ['ref']

    ref = me.StringField(required=True, unique=True)
    name = me.StringField(required=True, unique=True)
    description = me.StringField(required=True)
    keywords = me.ListField(field=me.StringField())
    version = me.StringField(required=True)  # TODO: Enforce format
    author = me.StringField(required=True)
    email = me.EmailField(required=True)
    files = me.ListField(field=me.StringField())

    meta = {
        'indexes': stormbase.UIDFieldMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(PackDB, self).__init__(*args, **values)
        self.uid = self.get_uid()


class ConfigSchemaDB(stormbase.StormFoundationDB):
    """
    System entity representing a config schema for a particular pack.
    """

    pack = me.StringField(
        required=True,
        unique=True,
        help_text='Name of the content pack this schema belongs to.')
    attributes = stormbase.EscapedDynamicField(
        help_text='The specification for config schema attributes.')


class ConfigDB(stormbase.StormFoundationDB):
    """
    System entity representing pack config.
    """
    pack = me.StringField(
        required=True,
        unique=True,
        help_text='Name of the content pack this config belongs to.')
    values = stormbase.EscapedDynamicField(
        help_text='Config values.')


# specialized access objects
pack_access = MongoDBAccess(PackDB)
config_schema_access = MongoDBAccess(ConfigSchemaDB)
config_access = MongoDBAccess(ConfigDB)

MODELS = [PackDB, ConfigSchemaDB, ConfigDB]
