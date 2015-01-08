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

from st2common.exceptions.access import TokenNotFoundError
from st2common.models.db import MongoDBAccess
from st2common.models.db.access import UserDB, TokenDB
from st2common.persistence.base import Access


class User(Access):
    impl = MongoDBAccess(UserDB)

    @classmethod
    def _get_impl(kls):
        return kls.impl


class Token(Access):
    impl = MongoDBAccess(TokenDB)

    @classmethod
    def _get_impl(kls):
        return kls.impl

    @classmethod
    def add_or_update(kls, model_object, publish=True):
        if not getattr(model_object, 'user', None):
            raise ValueError('User is not provided in the token.')
        if not getattr(model_object, 'token', None):
            raise ValueError('Token value is not set.')
        if not getattr(model_object, 'expiry', None):
            raise ValueError('Token expiry is not provided in the token.')
        return super(Token, kls).add_or_update(model_object, publish=publish)

    @classmethod
    def get(kls, value):
        for model_object in TokenDB.objects(token=value):
            return model_object
        raise TokenNotFoundError()
