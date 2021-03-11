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
import bson
import mock

from st2common.models.db.rule_enforcement import RuleEnforcementDB
from st2common.persistence.rule_enforcement import RuleEnforcement
from st2common.transport.publishers import PoolPublisher
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_SUCCEEDED
from st2common.constants.rule_enforcement import RULE_ENFORCEMENT_STATUS_FAILED
from st2common.exceptions.db import StackStormDBObjectNotFoundError

from st2tests import DbTestCase

SKIP_DELETE = False

__all__ = ["RuleEnforcementModelTest"]


@mock.patch.object(PoolPublisher, "publish", mock.MagicMock())
class RuleEnforcementModelTest(DbTestCase):
    def test_ruleenforcment_crud(self):
        saved = RuleEnforcementModelTest._create_save_rule_enforcement()
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertEqual(
            saved.rule.ref,
            retrieved.rule.ref,
            "Same rule enforcement was not returned.",
        )
        self.assertIsNotNone(retrieved.enforced_at)
        # test update
        RULE_ID = str(bson.ObjectId())
        self.assertEqual(retrieved.rule.id, None)
        retrieved.rule.id = RULE_ID
        saved = RuleEnforcement.add_or_update(retrieved)
        retrieved = RuleEnforcement.get_by_id(saved.id)
        self.assertEqual(
            retrieved.rule.id, RULE_ID, "Update to rule enforcement failed."
        )
        # cleanup
        RuleEnforcementModelTest._delete([retrieved])
        try:
            retrieved = RuleEnforcement.get_by_id(saved.id)
        except StackStormDBObjectNotFoundError:
            retrieved = None
        self.assertIsNone(retrieved, "managed to retrieve after delete.")

    def test_status_set_to_failed_for_objects_which_predate_status_field(self):
        rule = {"ref": "foo_pack.foo_rule", "uid": "rule:foo_pack:foo_rule"}

        # 1. No status field explicitly set and no failure reason
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule=rule,
            execution_id=str(bson.ObjectId()),
        )
        enforcement_db = RuleEnforcement.add_or_update(enforcement_db)

        self.assertEqual(enforcement_db.status, RULE_ENFORCEMENT_STATUS_SUCCEEDED)

        # 2. No status field, with failure reason, status should be set to failed
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule=rule,
            execution_id=str(bson.ObjectId()),
            failure_reason="so much fail",
        )
        enforcement_db = RuleEnforcement.add_or_update(enforcement_db)

        self.assertEqual(enforcement_db.status, RULE_ENFORCEMENT_STATUS_FAILED)

        # 3. Explcit status field - succeeded + failure reasun
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule=rule,
            execution_id=str(bson.ObjectId()),
            status=RULE_ENFORCEMENT_STATUS_SUCCEEDED,
            failure_reason="so much fail",
        )
        enforcement_db = RuleEnforcement.add_or_update(enforcement_db)

        self.assertEqual(enforcement_db.status, RULE_ENFORCEMENT_STATUS_FAILED)

        # 4. Explcit status field - succeeded + no failure reasun
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule=rule,
            execution_id=str(bson.ObjectId()),
            status=RULE_ENFORCEMENT_STATUS_SUCCEEDED,
        )
        enforcement_db = RuleEnforcement.add_or_update(enforcement_db)

        self.assertEqual(enforcement_db.status, RULE_ENFORCEMENT_STATUS_SUCCEEDED)

        # 5. Explcit status field - failed + no failure reasun
        enforcement_db = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule=rule,
            execution_id=str(bson.ObjectId()),
            status=RULE_ENFORCEMENT_STATUS_FAILED,
        )
        enforcement_db = RuleEnforcement.add_or_update(enforcement_db)

        self.assertEqual(enforcement_db.status, RULE_ENFORCEMENT_STATUS_FAILED)

    @staticmethod
    def _create_save_rule_enforcement():
        created = RuleEnforcementDB(
            trigger_instance_id=str(bson.ObjectId()),
            rule={"ref": "foo_pack.foo_rule", "uid": "rule:foo_pack:foo_rule"},
            execution_id=str(bson.ObjectId()),
        )
        return RuleEnforcement.add_or_update(created)

    @staticmethod
    def _delete(model_objects):
        global SKIP_DELETE
        if SKIP_DELETE:
            return
        for model_object in model_objects:
            model_object.delete()
