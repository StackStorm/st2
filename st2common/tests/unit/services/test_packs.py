# -*- coding: utf-8 -*-

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

import os
import os.path
import unittest2

import st2tests

from st2common.services.packs import delete_action_files_from_pack

TEST_PACK = "dummy_pack_1"
TEST_PACK_PATH = (
    st2tests.fixturesloader.get_fixtures_packs_base_path() + "/" + TEST_PACK
)


class DeleteActionFilesTest(unittest2.TestCase):

    entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
    metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

    # creating test entry_point file in pack
    with open(entry_point, "w") as f1:
        f1.write("# Entry point file to be removed")

    # creating test metadata file in pack
    with open(metadata_file, "w") as f1:
        f1.write("# Metadata file to be removed")

    def test_delete_action_files_from_pack(self):
        """
        Test that the action files present in the pack and removed
        on the call of delete_action_files_from_pack function.
        """

        self.assertEqual(os.path.exists(self.entry_point), True)
        self.assertEqual(os.path.exists(self.metadata_file), True)
        delete_action_files_from_pack(TEST_PACK, self.entry_point, self.metadata_file)
        self.assertEqual(os.path.exists(self.entry_point), False)
        self.assertEqual(os.path.exists(self.metadata_file), False)
