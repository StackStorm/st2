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

import copy
import mongoengine as me

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2common.models.db import stormbase
from st2common.services.rbac import get_roles_for_user
from st2common.constants.types import ResourceType

__all__ = [
    'UserDB',
    'TokenDB',
    'ApiKeyDB'
]


class UserDB(stormbase.StormFoundationDB):
    name = me.StringField(required=True, unique=True)

    def get_roles(self):
        """
        Retrieve roles assigned to that user.

        :rtype: ``list`` of :class:`RoleDB`
        """
        result = get_roles_for_user(user_db=self)
        return result

    def get_permission_assingments(self):
        # TODO
        pass


class TokenDB(stormbase.StormFoundationDB):
    user = me.StringField(required=True)
    token = me.StringField(required=True, unique=True)
    expiry = me.DateTimeField(required=True)
    metadata = me.DictField(required=False,
                            help_text='Arbitrary metadata associated with this token')


class ApiKeyDB(stormbase.StormFoundationDB, stormbase.UIDFieldMixin):
    """
    """
    RESOURCE_TYPE = ResourceType.API_KEY
    UID_FIELDS = ['id']

    user = me.StringField(required=True)
    key_hash = me.StringField(required=True, unique=True)
    metadata = me.DictField(required=False,
                            help_text='Arbitrary metadata associated with this token')

    meta = {
        'indexes': [
            {'fields': ['user']},
            {'fields': ['key_hash']}
        ]
    }

    def mask_secrets(self, value):
        result = copy.deepcopy(value)

        # In theory the key_hash is safe to return as it is one way. On the other
        # hand given that this is actually a secret no real point in letting the hash
        # escape.
        result['key_hash'] = MASKED_ATTRIBUTE_VALUE
        return result


MODELS = [UserDB, TokenDB, ApiKeyDB]
