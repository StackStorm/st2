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
from st2common.garbage_collection.rule_enforcement import purge_rule_enforcements
from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.util import date as date_utils
from st2tests.base import CleanDbTestCase

LOG = logging.getLogger(__name__)


class TestPurgeRuleEnforcement(CleanDbTestCase):
    @classmethod
    def setUpClass(cls):
        CleanDbTestCase.setUpClass()
        super(TestPurgeRuleEnforcement, cls).setUpClass()

    def setUp(self):
        super(TestPurgeRuleEnforcement, self).setUp()

    def test_no_timestamp_doesnt_delete(self):
        now = date_utils.get_datetime_utc_now()
        TestPurgeRuleEnforcement._create_save_rule_enforcement(
            enforced_at=now - timedelta(days=20),
        )

        self.assertEqual(len(RuleEnforcement.get_all()), 1)
        expected_msg = "Specify a valid timestamp"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            purge_rule_enforcements,
            logger=LOG,
            timestamp=None,
        )
        self.assertEqual(len(RuleEnforcement.get_all()), 1)

    def test_purge(self):
        now = date_utils.get_datetime_utc_now()
        TestPurgeRuleEnforcement._create_save_rule_enforcement(
            enforced_at=now - timedelta(days=20),
        )

        TestPurgeRuleEnforcement._create_save_rule_enforcement(
            enforced_at=now - timedelta(days=5),
        )

        self.assertEqual(len(RuleEnforcement.get_all()), 2)
        purge_rule_enforcements(logger=LOG, timestamp=now - timedelta(days=10))
        self.assertEqual(len(RuleEnforcement.get_all()), 1)

    @staticmethod
    def _create_save_rule_enforcement(enforced_at):
        created = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule={"ref": "foo_pack.foo_rule", "uid": "rule:foo_pack:foo_rule"},
            execution_id=str(bson.ObjectId()),
            enforced_at=enforced_at,
        )
        return RuleEnforcement.add_or_update(created)
