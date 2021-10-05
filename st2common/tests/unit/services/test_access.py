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
import uuid

from oslo_config import cfg
from st2tests.base import DbTestCase
from st2common.util import isotime
from st2common.util import date as date_utils
from st2common.exceptions.auth import TokenNotFoundError
from st2common.persistence.auth import Token
from st2common.services import access
from st2common.exceptions.auth import TTLTooLargeException
import st2tests.config as tests_config


USERNAME = "manas"


class AccessServiceTest(DbTestCase):
    @classmethod
    def setUpClass(cls):
        super(AccessServiceTest, cls).setUpClass()
        tests_config.parse_args()

    def test_create_token(self):
        token = access.create_token(USERNAME)
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.token)
        self.assertEqual(token.user, USERNAME)

    def test_create_token_fail(self):
        try:
            access.create_token(None)
            self.assertTrue(False, "Create succeeded was expected to fail.")
        except ValueError:
            self.assertTrue(True)

    def test_delete_token(self):
        token = access.create_token(USERNAME)
        access.delete_token(token.token)
        try:
            token = Token.get(token.token)
            self.assertTrue(False, "Delete failed was expected to pass.")
        except TokenNotFoundError:
            self.assertTrue(True)

    def test_delete_non_existent_token(self):
        token = uuid.uuid4().hex
        self.assertRaises(TokenNotFoundError, Token.get, token)
        access.delete_token(token)

    def test_create_token_ttl_ok(self):
        ttl = 10
        token = access.create_token(USERNAME, 10)
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.token)
        self.assertEqual(token.user, USERNAME)
        expected_expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=ttl
        )
        expected_expiry = date_utils.add_utc_tz(expected_expiry)
        self.assertLess(isotime.parse(token.expiry), expected_expiry)

    def test_create_token_ttl_capped(self):
        ttl = cfg.CONF.auth.token_ttl + 10
        expected_expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=ttl
        )
        expected_expiry = date_utils.add_utc_tz(expected_expiry)
        token = access.create_token(USERNAME, 10)
        self.assertIsNotNone(token)
        self.assertIsNotNone(token.token)
        self.assertEqual(token.user, USERNAME)
        self.assertLess(isotime.parse(token.expiry), expected_expiry)

    def test_create_token_service_token_can_use_arbitrary_ttl(self):
        ttl = 10000 * 24 * 24

        # Service token should support arbitrary TTL
        token = access.create_token(USERNAME, ttl=ttl, service=True)
        expected_expiry = date_utils.get_datetime_utc_now() + datetime.timedelta(
            seconds=ttl
        )
        expected_expiry = date_utils.add_utc_tz(expected_expiry)

        self.assertIsNotNone(token)
        self.assertEqual(token.user, USERNAME)
        self.assertLess(isotime.parse(token.expiry), expected_expiry)

        # Non service token should throw on TTL which is too large
        self.assertRaises(
            TTLTooLargeException, access.create_token, USERNAME, ttl=ttl, service=False
        )
