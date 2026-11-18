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

import mock
import six

from st2common.persistence.execution import ActionExecution
from st2common.rbac.backends.noop import NoOpRBACUtils
from st2tests.fixtures.descendants.fixture import PACK_NAME as DESCENDANTS_PACK
from st2tests.fixturesloader import FixturesLoader
from st2tests.api import FunctionalTest


DESCENDANTS_FIXTURES = {
    "executions": [
        "root_execution.yaml",
        "child1_level1.yaml",
        "child2_level1.yaml",
        "child1_level2.yaml",
        "child2_level2.yaml",
        "child3_level2.yaml",
        "child1_level3.yaml",
        "child2_level3.yaml",
        "child3_level3.yaml",
    ],
    "liveactions": ["liveaction_fake.yaml"],
}


class ActionExecutionControllerTestCaseDescendantsTest(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(ActionExecutionControllerTestCaseDescendantsTest, cls).setUpClass()
        cls.MODELS = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=DESCENDANTS_PACK,
            fixtures_dict=DESCENDANTS_FIXTURES,
            use_object_ids=True,
        )

    def test_get_all_descendants(self):
        root_execution = self.MODELS["executions"]["root_execution.yaml"]
        resp = self.app.get("/v1/executions/%s/children" % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant["id"] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [
            str(v.id)
            for _, v in six.iteritems(self.MODELS["executions"])
            if v.id != root_execution.id
        ]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_all_descendants_depth_neg_1(self):
        root_execution = self.MODELS["executions"]["root_execution.yaml"]
        resp = self.app.get(
            "/v1/executions/%s/children?depth=-1" % str(root_execution.id)
        )
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant["id"] for descendant in resp.json]
        all_descendants_ids.sort()

        # everything except the root_execution
        expected_ids = [
            str(v.id)
            for _, v in six.iteritems(self.MODELS["executions"])
            if v.id != root_execution.id
        ]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)

    def test_get_1_level_descendants(self):
        root_execution = self.MODELS["executions"]["root_execution.yaml"]
        resp = self.app.get(
            "/v1/executions/%s/children?depth=1" % str(root_execution.id)
        )
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = [descendant["id"] for descendant in resp.json]
        all_descendants_ids.sort()

        # All children of root_execution
        expected_ids = [
            str(v.id)
            for _, v in six.iteritems(self.MODELS["executions"])
            if v.parent == str(root_execution.id)
        ]
        expected_ids.sort()

        self.assertListEqual(all_descendants_ids, expected_ids)


VISIBLE_ACTION_UID = "action:descendants:visible"
HIDDEN_ACTION_UID = "action:descendants:hidden"

DESCENDANT_ACTION_UIDS = {
    "child1_level1.yaml": VISIBLE_ACTION_UID,
    "child2_level1.yaml": VISIBLE_ACTION_UID,
    "child1_level2.yaml": VISIBLE_ACTION_UID,
    "child2_level2.yaml": VISIBLE_ACTION_UID,
    "child3_level2.yaml": VISIBLE_ACTION_UID,
    "child1_level3.yaml": HIDDEN_ACTION_UID,
    "child2_level3.yaml": HIDDEN_ACTION_UID,
    # child3_level3.yaml keeps the fixture's action, which has no uid.
}


def _can_view_visible_action(user_db, resource_db, permission_type):
    return resource_db.action.get("uid") == VISIBLE_ACTION_UID


class ActionExecutionControllerTestCaseDescendantsPermissionsTest(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(
            ActionExecutionControllerTestCaseDescendantsPermissionsTest, cls
        ).setUpClass()
        cls.MODELS = FixturesLoader().save_fixtures_to_db(
            fixtures_pack=DESCENDANTS_PACK,
            fixtures_dict=DESCENDANTS_FIXTURES,
            use_object_ids=True,
        )
        for name, action_uid in six.iteritems(DESCENDANT_ACTION_UIDS):
            execution = cls.MODELS["executions"][name]
            execution.action = dict(execution.action, uid=action_uid)
            ActionExecution.add_or_update(execution)

    @mock.patch.object(
        NoOpRBACUtils,
        "user_has_resource_db_permission",
        mock.MagicMock(side_effect=_can_view_visible_action),
    )
    def test_get_descendants_filtered_by_permission(self):
        root_execution = self.MODELS["executions"]["root_execution.yaml"]
        resp = self.app.get("/v1/executions/%s/children" % str(root_execution.id))
        self.assertEqual(resp.status_int, 200)

        all_descendants_ids = sorted(descendant["id"] for descendant in resp.json)
        # All the VISIBLE_ACTION_UID names above
        expected_names = (
            "child1_level1.yaml",
            "child2_level1.yaml",
            "child1_level2.yaml",
            "child2_level2.yaml",
            "child3_level2.yaml",
        )
        expected_ids = sorted(
            str(self.MODELS["executions"][name].id) for name in expected_names
        )
        self.assertListEqual(all_descendants_ids, expected_ids)

        # Once per action uid, plus once for the descendant without one.
        self.assertEqual(NoOpRBACUtils.user_has_resource_db_permission.call_count, 3)
