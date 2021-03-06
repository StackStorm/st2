#!/usr/bin/env python

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

from st2tests.base import BaseActionTestCase

from pack_mgmt.virtualenv_setup_prerun import PacksTransformationAction


class VirtualenvSetUpPreRunTestCase(BaseActionTestCase):
    action_cls = PacksTransformationAction

    def setUp(self):
        super(VirtualenvSetUpPreRunTestCase, self).setUp()

    def test_run_with_pack_list(self):
        action = self.get_action_instance()
        result = action.run(
            packs_status={"test1": "Success.", "test2": "Success."},
            packs_list=["test3", "test4"],
        )

        self.assertEqual(result, ["test3", "test4", "test1", "test2"])

    def test_run_with_none_pack_list(self):
        action = self.get_action_instance()
        result = action.run(
            packs_status={"test1": "Success.", "test2": "Success."}, packs_list=None
        )

        self.assertEqual(result, ["test1", "test2"])

    def test_run_with_failed_status(self):
        action = self.get_action_instance()
        result = action.run(
            packs_status={"test1": "Failed.", "test2": "Success."},
            packs_list=["test3", "test4"],
        )

        self.assertEqual(result, ["test3", "test4", "test2"])
