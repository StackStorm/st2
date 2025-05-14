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

# This import must be early for import-time side-effects.
from st2tests import base

import mock

from st2common.runners import utils
from st2common.services import executions as exe_svc
from st2common.util import action_db as action_db_utils
from st2tests import fixturesloader
from st2tests.fixtures.generic.fixture import PACK_NAME as FIXTURES_PACK


TEST_FIXTURES = {
    "liveactions": ["liveaction1.yaml"],
    "actions": ["local.yaml"],
    "executions": ["execution1.yaml"],
    "runners": ["run-local.yaml"],
}


class RunnersUtilityTests(base.CleanDbTestCase):
    def __init__(self, *args, **kwargs):
        super(RunnersUtilityTests, self).__init__(*args, **kwargs)
        self.models = None

    def setUp(self):
        super(RunnersUtilityTests, self).setUp()

        loader = fixturesloader.FixturesLoader()

        self.models = loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES
        )

        self.liveaction_db = self.models["liveactions"]["liveaction1.yaml"]
        exe_svc.create_execution_object(self.liveaction_db)
        self.action_db = action_db_utils.get_action_by_ref(self.liveaction_db.action)

    @mock.patch.object(
        action_db_utils, "get_action_by_ref", mock.MagicMock(return_value=None)
    )
    def test_invoke_post_run_action_provided(self):
        utils.invoke_post_run(self.liveaction_db, action_db=self.action_db)
        action_db_utils.get_action_by_ref.assert_not_called()

    def test_invoke_post_run_action_exists(self):
        utils.invoke_post_run(self.liveaction_db)

    @mock.patch.object(
        action_db_utils, "get_action_by_ref", mock.MagicMock(return_value=None)
    )
    @mock.patch.object(
        action_db_utils, "get_runnertype_by_name", mock.MagicMock(return_value=None)
    )
    def test_invoke_post_run_action_does_not_exist(self):
        utils.invoke_post_run(self.liveaction_db)
        action_db_utils.get_action_by_ref.assert_called_once()
        action_db_utils.get_runnertype_by_name.assert_not_called()
