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
from st2common.models.db.auth import UserDB
from st2common.models.db.auth import TokenDB
from st2common.models.db.auth import ApiKeyDB
from st2common.persistence.auth import User
from st2common.persistence.auth import Token
from st2common.persistence.auth import ApiKey
from st2common.util.date import get_datetime_utc_now
from st2tests import DbTestCase

from tests.unit.base import BaseDBModelCRUDTestCase


__all__ = ["UserDBModelCRUDTestCase"]


class UserDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = UserDB
    persistance_class = User
    model_class_kwargs = {
        "name": "pony",
        "is_service": False,
        "nicknames": {"pony1": "ponyA"},
    }
    update_attribute_name = "name"


class TokenDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = TokenDB
    persistance_class = Token
    model_class_kwargs = {
        "user": "pony",
        "token": "token-token-token-token",
        "expiry": get_datetime_utc_now(),
        "metadata": {"service": "action-runner"},
    }
    skip_check_attribute_names = ["expiry"]
    update_attribute_name = "user"


class ApiKeyDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = ApiKeyDB
    persistance_class = ApiKey
    model_class_kwargs = {"user": "pony", "key_hash": "token-token-token-token"}
    update_attribute_name = "user"
