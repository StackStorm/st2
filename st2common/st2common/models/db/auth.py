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

from st2common.models.db import stormbase
from st2common.services.rbac import get_roles_for_user

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


class ApiKeyDB(stormbase.StormFoundationDB):
    """
    """
    user = me.StringField(required=True)
    key = me.StringField(required=True, unique=True)
    metadata = me.DictField(required=False,
                            help_text='Arbitrary metadata associated with this token')

    meta = {
        'indexes': [
            {'fields': ['key']}
        ]
    }


MODELS = [UserDB, TokenDB, ApiKeyDB]
