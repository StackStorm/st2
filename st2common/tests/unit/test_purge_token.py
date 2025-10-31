# Copyright 2022 The StackStorm Authors.
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

# pytest: make sure monkey_patching happens before importing mongoengine
from st2common.util.monkey_patch import monkey_patch

monkey_patch()

from datetime import timedelta
import bson

from st2common import log as logging
from st2common.garbage_collection.token import purge_tokens
from st2common.models.db.auth import TokenDB
from st2common.persistence.auth import Token
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase

LOG = logging.getLogger(__name__)


class TestPurgeToken(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeToken, cls).setUpClass()

    def setUp(self):
        super(TestPurgeToken, self).setUp()

    def test_no_timestamp_doesnt_delete(self):
        now = date_utils.get_datetime_utc_now()
        TestPurgeToken._create_save_token(
            expiry_timestamp=now - timedelta(days=20),
        )

        self.assertEqual(len(Token.get_all()), 1)
        expected_msg = "Specify a valid timestamp"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            purge_tokens,
            logger=LOG,
            timestamp=None,
        )
        self.assertEqual(len(Token.get_all()), 1)

    def test_purge(self):
        now = date_utils.get_datetime_utc_now()
        TestPurgeToken._create_save_token(
            expiry_timestamp=now - timedelta(days=20),
        )

        TestPurgeToken._create_save_token(
            expiry_timestamp=now - timedelta(days=5),
        )

        self.assertEqual(len(Token.get_all()), 2)
        purge_tokens(logger=LOG, timestamp=now - timedelta(days=10))
        self.assertEqual(len(Token.get_all()), 1)

    @staticmethod
    def _create_save_token(expiry_timestamp=None):
        created = TokenDB(
            id=str(bson.ObjectId()),
            user="pony",
            token=str(bson.ObjectId()),
            expiry=expiry_timestamp,
            metadata={"service": "action-runner"},
        )
        return Token.add_or_update(created)
