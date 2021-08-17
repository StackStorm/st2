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
import mock
import unittest2

import st2tests

from st2common.services.packs import delete_action_files_from_pack

TEST_PACK = "dummy_pack_1"
TEST_PACK_PATH = os.path.join(
    st2tests.fixturesloader.get_fixtures_packs_base_path(), TEST_PACK
)


class DeleteActionFilesTest(unittest2.TestCase):
    def test_delete_action_files_from_pack(self):
        """
        Test that the action files present in the pack and removed
        on the call of delete_action_files_from_pack function.
        """

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        # creating entry_point file in dummy pack
        with open(entry_point, "w") as f:
            f.write("# entry point file to be removed")

        # creating metadata file in dummy pack
        with open(metadata_file, "w") as f:
            f.write("# metadata file to be removed")

        # asserting both entry_point and metadata files exists
        self.assertTrue(os.path.exists(entry_point))
        self.assertTrue(os.path.exists(metadata_file))

        delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)

        # asserting both entry_point and metadata files removed and they doesn't exist
        self.assertFalse(os.path.exists(entry_point))
        self.assertFalse(os.path.exists(metadata_file))

    def test_entry_point_file_does_not_exists(self):
        """
        Tests that entry_point file doesn't exists at the path and if action delete
        api calls delete_action_files_from_pack function, it doesn't affect.
        """

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        # creating only metadata file in dummy pack
        with open(metadata_file, "w") as f:
            f.write("# metadata file to be removed")

        # asserting entry_point file doesn't exist
        self.assertFalse(os.path.exists(entry_point))

        # asserting metadata files exists
        self.assertTrue(os.path.exists(metadata_file))

        delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)

        # asserting both entry_point and metadata files don't exist
        self.assertFalse(os.path.exists(entry_point))
        self.assertFalse(os.path.exists(metadata_file))

    def test_metadata_file_does_not_exists(self):
        """
        Tests that metadata file doesn't exists at the path and if action delete
        api calls delete_action_files_from_pack function, it doesn't affect.
        """

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        # creating only entry_point file in dummy pack
        with open(entry_point, "w") as f:
            f.write("# entry point file to be removed")

        # asserting metadata file doesn't exist
        self.assertFalse(os.path.exists(metadata_file))

        # asserting entry_point file exists
        self.assertTrue(os.path.exists(entry_point))

        delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)

        # asserting both entry_point and metadata files don't exist
        self.assertFalse(os.path.exists(entry_point))
        self.assertFalse(os.path.exists(metadata_file))


class DeleteActionEntryPointFilesErrorTest(unittest2.TestCase):
    """
    Testing that exceptions are thrown by delete_action_files_from_pack function
    for entry point file. Here only entry point file is created and metadata
    file doesn't exist.
    """

    def setUp(self):
        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")

        # creating entry_point file in dummy pack
        with open(entry_point, "w") as f:
            f.write("# entry point file to be removed")

    def tearDown(self):
        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")

        # removing entry_point file from dummy pack
        os.remove(entry_point)

    @mock.patch.object(os, "remove")
    def test_permission_error_to_remove_resource_entry_point_file(self, remove):

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        remove.side_effect = PermissionError("No permission to delete file from disk")

        # asserting entry_point file exists
        self.assertTrue(os.path.exists(entry_point))

        # asserting metadata file doesn't exist
        self.assertFalse(os.path.exists(metadata_file))

        expected_msg = 'No permission to delete "%s" file from disk' % (entry_point)

        # asserting PermissionError with message on call of delete_action_files_from_pack
        # to delete entry_point file
        with self.assertRaisesRegexp(PermissionError, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)

    @mock.patch.object(os, "remove")
    def test_exception_to_remove_resource_entry_point_file(self, remove):

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        remove.side_effect = Exception("Another exception occured")

        # asserting entry_point file exists
        self.assertTrue(os.path.exists(entry_point))

        # asserting metadata file doesn't exist
        self.assertFalse(os.path.exists(metadata_file))

        expected_msg = (
            'The action file "%s" could not be removed from disk, please '
            "check the logs or ask your StackStorm administrator to check "
            "and delete the actions files manually" % (entry_point)
        )

        # asserting exception with message on call of delete_action_files_from_pack
        # to delete entry_point file
        with self.assertRaisesRegexp(Exception, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)


class DeleteActionMetadataFilesErrorTest(unittest2.TestCase):
    """
    Testing that exceptions are thrown by delete_action_files_from_pack function for
    metadata file. Here only metadata file is created and metadata file doesn't exist.
    """

    def setUp(self):
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        # creating metadata file in dummy pack
        with open(metadata_file, "w") as f:
            f.write("# metadata file to be removed")

    def tearDown(self):
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        # removing metadata file from dummy pack
        os.remove(metadata_file)

    @mock.patch.object(os, "remove")
    def test_permission_error_to_remove_resource_metadata_file(self, remove):

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        remove.side_effect = PermissionError("No permission to delete file from disk")

        # asserting metadata file exists
        self.assertTrue(os.path.exists(metadata_file))

        # asserting entry_point file doesn't exist
        self.assertFalse(os.path.exists(entry_point))

        expected_msg = 'No permission to delete "%s" file from disk' % (metadata_file)

        # asserting PermissionError with message on call of delete_action_files_from_pack
        # to delete metadata file
        with self.assertRaisesRegexp(PermissionError, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)

    @mock.patch.object(os, "remove")
    def test_exception_to_remove_resource_metadata_file(self, remove):

        entry_point = os.path.join(TEST_PACK_PATH, "actions", "test_entry_point.py")
        metadata_file = os.path.join(TEST_PACK_PATH, "actions", "test_metadata.yaml")

        remove.side_effect = Exception("Another exception occured")

        # asserting metadata file exists
        self.assertTrue(os.path.exists(metadata_file))

        # asserting entry_point file doesn't exist
        self.assertFalse(os.path.exists(entry_point))

        expected_msg = (
            'The action file "%s" could not be removed from disk, please '
            "check the logs or ask your StackStorm administrator to check "
            "and delete the actions files manually" % (metadata_file)
        )

        # asserting exception with message on call of delete_action_files_from_pack
        # to delete metadata file
        with self.assertRaisesRegexp(Exception, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)
