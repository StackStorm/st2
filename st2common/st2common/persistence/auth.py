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

from st2common.exceptions.auth import TokenNotFoundError, ApiKeyNotFoundError
from st2common.models.db import MongoDBAccess
from st2common.models.db.auth import UserDB, TokenDB, ApiKeyDB
from st2common.persistence.base import Access


class User(Access):
    impl = MongoDBAccess(UserDB)

    @classmethod
    def get(cls, username):
        return cls.get_by_name(username)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def _get_by_object(cls, object):
        # For User name is unique.
        name = getattr(object, 'name', '')
        return cls.get_by_name(name)


class Token(Access):
    impl = MongoDBAccess(TokenDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def add_or_update(cls, model_object, publish=True):
        if not getattr(model_object, 'user', None):
            raise ValueError('User is not provided in the token.')
        if not getattr(model_object, 'token', None):
            raise ValueError('Token value is not set.')
        if not getattr(model_object, 'expiry', None):
            raise ValueError('Token expiry is not provided in the token.')
        return super(Token, cls).add_or_update(model_object, publish=publish)

    @classmethod
    def get(cls, value):
        for model_object in TokenDB.objects(token=value):
            return model_object
        raise TokenNotFoundError()


class ApiKey(Access):
    impl = MongoDBAccess(ApiKeyDB)

    @classmethod
    def _get_impl(cls):
        return cls.impl

    @classmethod
    def get(cls, value):
        for model_object in ApiKeyDB.objects(key=value):
            return model_object
        raise ApiKeyNotFoundError('ApiKey with key=%s not found.', value)

    @classmethod
    def get_by_key_or_id(cls, value):
        try:
            return cls.get(value)
        except ApiKeyNotFoundError:
            pass
        try:
            return cls.get_by_id(value)
        except:
            raise ApiKeyNotFoundError('ApiKey with key or id=%s not found.', value)
