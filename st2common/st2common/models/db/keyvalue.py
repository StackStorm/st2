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
    'KeyValuePairDB'
]


class KeyValuePairDB(stormbase.StormBaseDB, stormbase.UIDFieldMixin):
    """
    Attribute:
        name: Name of the key.
        value: Arbitrary value to be stored.
    """

    RESOURCE_TYPE = ResourceType.KEY_VALUE_PAIR
    UID_FIELDS = ['name']

    name = me.StringField(required=True, unique=True)
    value = me.StringField()
    expire_timestamp = me.DateTimeField()

    meta = {
        'indexes': [
            {
                'fields': ['expire_timestamp'],
                'expireAfterSeconds': 0
            }
        ] + stormbase.UIDFieldMixin.get_indexes()
    }

    def __init__(self, *args, **values):
        super(KeyValuePairDB, self).__init__(*args, **values)
        self.uid = self.get_uid()


# specialized access objects
keyvaluepair_access = MongoDBAccess(KeyValuePairDB)

MODELS = [KeyValuePairDB]
