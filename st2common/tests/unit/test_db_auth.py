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
import datetime
from st2common.models.db.auth import SSORequestDB, UserDB
from st2common.models.db.auth import TokenDB
from st2common.models.db.auth import ApiKeyDB
from st2common.persistence.auth import SSORequest, User
from st2common.persistence.auth import Token
from st2common.persistence.auth import ApiKey
from st2common.util.date import add_utc_tz, get_datetime_utc_now
from st2tests import DbTestCase
from mongoengine.errors import ValidationError

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


class SSORequestDBModelCRUDTestCase(BaseDBModelCRUDTestCase, DbTestCase):
    model_class = SSORequestDB
    persistance_class = SSORequest
    model_class_kwargs = {
        "request_id": "48144c2b-7969-4708-ba1d-96fd7d05393f",
        "expiry": add_utc_tz(
            datetime.datetime.strptime("2050-01-05T10:00:00", "%Y-%m-%dT%H:%M:%S")
        ),
        "type": SSORequestDB.Type.CLI,
    }
    update_attribute_name = "request_id"

    def _save_model(self, **kwargs):
        model_db = self.model_class(**kwargs)
        self.persistance_class.add_or_update(model_db)

    def test_missing_parameters(self):

        self.assertRaises(
            ValueError,
            self._save_model,
            **{
                "request_id": self.model_class_kwargs["request_id"],
                "expiry": self.model_class_kwargs["expiry"],
            },
        )

        self.assertRaises(
            ValueError,
            self._save_model,
            **{
                "request_id": self.model_class_kwargs["request_id"],
                "type": self.model_class_kwargs["type"],
            },
        )

        self.assertRaises(
            ValueError,
            self._save_model,
            **{
                "type": self.model_class_kwargs["type"],
                "expiry": self.model_class_kwargs["expiry"],
            },
        )

    def test_invalid_parameters(self):

        self.assertRaises(
            ValidationError,
            self._save_model,
            **{
                "type": "invalid",
                "expiry": self.model_class_kwargs["expiry"],
                "request_id": self.model_class_kwargs["request_id"],
            },
        )
