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
import shutil
import unittest
import uuid

from st2common.models.db.stormbase import UIDFieldMixin
from st2common.services.packs import delete_action_files_from_pack
from st2common.services.packs import clone_action_files
from st2common.services.packs import clone_action_db
from st2common.services.packs import temp_backup_action_files
from st2common.services.packs import restore_temp_action_files
from st2common.services.packs import remove_temp_action_files

from st2tests.fixtures.packs.core.fixture import PACK_NAME as TEST_SOURCE_PACK
from st2tests.fixtures.packs.dummy_pack_1.fixture import (
    PACK_NAME as TEST_PACK,
    PACK_PATH as TEST_PACK_PATH,
)
from st2tests.fixtures.packs.dummy_pack_23.fixture import (
    PACK_NAME as TEST_DEST_PACK,
    PACK_PATH as TEST_DEST_PACK_PATH,
)
from st2tests.fixtures.packs.orquesta_tests.fixture import (
    PACK_NAME as TEST_SOURCE_WORKFLOW_PACK,
)
import st2tests.config as tests_config

SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER = {
    "description": "Action which injects a new trigger in the system.",
    "enabled": True,
    "entry_point": "inject_trigger.py",
    "metadata_file": "actions/inject_trigger.yaml",
    "name": "inject_trigger",
    "notify": {},
    "output_schema": {},
    "pack": TEST_SOURCE_PACK,
    "parameters": {
        "trigger": {
            "type": "string",
            "description": "Trigger reference (e.g. mypack.my_trigger).",
            "required": True,
        },
        "payload": {"type": "object", "description": "Trigger payload."},
        "trace_tag": {
            "type": "string",
            "description": "Optional trace tag.",
            "required": False,
        },
    },
    "ref": "core.inject_trigger",
    "runner_type": {"name": "python-script"},
    "tags": [],
    "uid": "action:core:inject_trigger",
}

SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER = {
    "description": "This sends an email",
    "enabled": True,
    "entry_point": "send_mail/send_mail",
    "metadata_file": "actions/sendmail.yaml",
    "name": "sendmail",
    "notify": {},
    "output_schema": {},
    "pack": TEST_SOURCE_PACK,
    "parameters": {
        "sendmail_binary": {
            "description": "Optional path to the sendmail binary. If not provided, it uses a system default one.",
            "position": 0,
            "required": False,
            "type": "string",
            "default": "None",
        },
        "from": {
            "description": "Sender email address.",
            "position": 1,
            "required": False,
            "type": "string",
            "default": "stanley",
        },
        "to": {
            "description": "Recipient email address.",
            "position": 2,
            "required": True,
            "type": "string",
        },
        "subject": {
            "description": "Subject of the email.",
            "position": 3,
            "required": True,
            "type": "string",
        },
        "send_empty_body": {
            "description": "Send a message even if the body is empty.",
            "position": 4,
            "required": False,
            "type": "boolean",
            "default": True,
        },
        "content_type": {
            "type": "string",
            "description": "Content type of message to be sent without the charset (charset is set to UTF-8 inside the script).",
            "default": "text/html",
            "position": 5,
        },
        "body": {
            "description": "Body of the email.",
            "position": 6,
            "required": True,
            "type": "string",
        },
        "sudo": {"immutable": True},
        "attachments": {
            "description": "Array of attachment file paths, comma-delimited.",
            "position": 7,
            "required": False,
            "type": "string",
        },
    },
    "ref": "core.sendmail",
    "runner_type": {"name": "local-shell-script"},
    "tags": [],
    "uid": "action:core:sendmail",
}

SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER = {
    "description": "Action that executes the Linux echo command on the localhost.",
    "enabled": True,
    "entry_point": "",
    "metadata_file": "actions/echo.yaml",
    "name": "echo",
    "notify": {},
    "output_schema": {},
    "pack": TEST_SOURCE_PACK,
    "parameters": {
        "message": {
            "description": "The message that the command will echo.",
            "type": "string",
            "required": True,
        },
        "cmd": {
            "description": "Arbitrary Linux command to be executed on the local host.",
            "required": True,
            "type": "string",
            "default": 'echo "{{message}}"',
            "immutable": True,
        },
        "kwarg_op": {"immutable": True},
        "sudo": {"default": False, "immutable": True},
        "sudo_password": {"immutable": True},
    },
    "ref": "core.echo",
    "runner_type": {"name": "local-shell-cmd"},
    "tags": [],
    "uid": "action:core:echo",
}

# source workflow needed from ``/st2tests/fixtures/packs/`` path. When source workflow
# taken from ``/opt/stackstorm/packs/`` path, related unit tests fail
SOURCE_WORKFLOW = {
    "description": "A basic workflow to demonstrate data flow options.",
    "enabled": True,
    "entry_point": "workflows/data-flow.yaml",
    "metadata_file": "actions/data-flow.yaml",
    "name": "data-flow",
    "notify": {},
    "output_schema": {
        "type": "object",
        "properties": {
            "a6": {"type": "string", "required": True},
            "b6": {"type": "string", "required": True},
            "a7": {"type": "string", "required": True},
            "b7": {"type": "string", "required": True, "secret": True},
        },
        "additionalProperties": False,
    },
    "pack": TEST_SOURCE_WORKFLOW_PACK,
    "parameters": {"a1": {"required": True, "type": "string"}},
    "ref": "orquesta_tests.data-flow",
    "runner_type": {"name": "orquesta"},
    "tags": [],
    "uid": "action:orquesta_tests:data-flow",
}


class DeleteActionFilesTest(unittest.TestCase):
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


class DeleteActionEntryPointFilesErrorTest(unittest.TestCase):
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
        with self.assertRaisesRegex(PermissionError, expected_msg):
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
        with self.assertRaisesRegex(Exception, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)


class DeleteActionMetadataFilesErrorTest(unittest.TestCase):
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
        with self.assertRaisesRegex(PermissionError, expected_msg):
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
        with self.assertRaisesRegex(Exception, expected_msg):
            delete_action_files_from_pack(TEST_PACK, entry_point, metadata_file)


class CloneActionDBAndFilesTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()
        action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        workflow_files_path = os.path.join(action_files_path, "workflows")
        if not os.path.isdir(action_files_path):
            os.mkdir(action_files_path)
        if not os.path.isdir(workflow_files_path):
            os.mkdir(workflow_files_path)

    @classmethod
    def tearDownClass(cls):
        action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        workflow_files_path = os.path.join(action_files_path, "workflows")
        if not os.path.isdir(action_files_path):
            os.mkdir(action_files_path)
        if not os.path.isdir(workflow_files_path):
            os.mkdir(workflow_files_path)
        for file in os.listdir(action_files_path):
            if os.path.isfile(os.path.join(action_files_path, file)):
                os.remove(os.path.join(action_files_path, file))
        for file in os.listdir(workflow_files_path):
            if os.path.isfile(os.path.join(workflow_files_path, file)):
                os.remove(os.path.join(workflow_files_path, file))

    def test_clone_action_db(self):
        CLONE_ACTION_1 = clone_action_db(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_1"
        )
        exptected_uid = UIDFieldMixin.UID_SEPARATOR.join(
            ["action", TEST_DEST_PACK, "clone_action_1"]
        )
        actual_uid = CLONE_ACTION_1["uid"]
        self.assertEqual(actual_uid, exptected_uid)
        exptected_parameters = SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER["parameters"]
        actual_parameters = CLONE_ACTION_1["parameters"]
        self.assertDictEqual(actual_parameters, exptected_parameters)

    def test_clone_files_for_python_script_runner_action(self):
        CLONE_ACTION_1 = clone_action_db(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_1"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, CLONE_ACTION_1, TEST_DEST_PACK_PATH
        )
        cloned_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_1.yaml"
        )
        cloned_action_entry_point_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_1.py"
        )
        self.assertTrue(os.path.exists(cloned_action_metadata_file_path))
        self.assertTrue(os.path.exists(cloned_action_entry_point_file_path))

    def test_clone_files_for_shell_script_runner_action(self):
        CLONE_ACTION_2 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_2"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, CLONE_ACTION_2, TEST_DEST_PACK_PATH
        )
        cloned_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_2.yaml"
        )
        cloned_action_entry_point_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_2"
        )
        self.assertTrue(os.path.exists(cloned_action_metadata_file_path))
        self.assertTrue(os.path.exists(cloned_action_entry_point_file_path))

    def test_clone_files_for_local_shell_cmd_runner_action(self):
        CLONE_ACTION_3 = clone_action_db(
            SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER, TEST_DEST_PACK, "clone_action_3"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER,
            CLONE_ACTION_3,
            TEST_DEST_PACK_PATH,
        )
        cloned_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_3.yaml"
        )
        self.assertTrue(os.path.exists(cloned_action_metadata_file_path))

    def test_clone_files_for_workflow_action(self):
        CLONE_WORKFLOW = clone_action_db(
            SOURCE_WORKFLOW, TEST_DEST_PACK, "clone_workflow"
        )
        clone_action_files(SOURCE_WORKFLOW, CLONE_WORKFLOW, TEST_DEST_PACK_PATH)
        cloned_workflow_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_workflow.yaml"
        )
        cloned_workflow_entry_point_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "workflows", "clone_workflow.yaml"
        )
        self.assertTrue(os.path.exists(cloned_workflow_metadata_file_path))
        self.assertTrue(os.path.exists(cloned_workflow_entry_point_file_path))

    @mock.patch("shutil.copy")
    def test_permission_error_to_write_in_destination_file(self, mock_copy):
        mock_copy.side_effect = PermissionError("No permission to write in file")
        cloned_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_4.yaml"
        )
        expected_msg = 'Unable to copy file to "%s".' % (
            cloned_action_metadata_file_path
        )
        CLONE_ACTION_4 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_4"
        )
        with self.assertRaisesRegex(PermissionError, expected_msg):
            clone_action_files(
                SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER,
                CLONE_ACTION_4,
                TEST_DEST_PACK_PATH,
            )

    @mock.patch("shutil.copy")
    def test_exceptions_to_write_in_destination_file(self, mock_copy):
        mock_copy.side_effect = Exception(
            "Exception encoutntered during writing in destination action file"
        )
        CLONE_ACTION_5 = clone_action_db(
            SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER, TEST_DEST_PACK, "clone_action_5"
        )
        cloned_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", "clone_action_5.yaml"
        )
        expected_msg = (
            'Unable to copy file to "%s". Please check the logs or ask your '
            "administrator to clone the files manually."
            % cloned_action_metadata_file_path
        )
        with self.assertRaisesRegex(Exception, expected_msg):
            clone_action_files(
                SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER,
                CLONE_ACTION_5,
                TEST_DEST_PACK_PATH,
            )

    def test_actions_directory_created_if_does_not_exist(self):
        action_dir_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        # removing actions directory and asserting it doesn't exist
        shutil.rmtree(action_dir_path)
        self.assertFalse(os.path.exists(action_dir_path))
        CLONE_ACTION_6 = clone_action_db(
            SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER, TEST_DEST_PACK, "clone_action_6"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_LOCAL_SHELL_CMD_RUNNER,
            CLONE_ACTION_6,
            TEST_DEST_PACK_PATH,
        )
        # workflows directory created and asserting it exists
        self.assertTrue(os.path.exists(action_dir_path))
        wf_dir_path = os.path.join(action_dir_path, "workflows")
        if not os.path.isdir(wf_dir_path):
            os.mkdir(wf_dir_path)

    def test_workflows_directory_created_if_does_not_exist(self):
        action_dir_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        workflows_dir_path = os.path.join(TEST_DEST_PACK_PATH, "actions", "workflows")
        # removing workflows directory and asserting it doesn't exist
        shutil.rmtree(workflows_dir_path)
        self.assertFalse(os.path.exists(workflows_dir_path))
        self.assertTrue(os.path.exists(action_dir_path))
        CLONE_WORKFLOW = clone_action_db(
            SOURCE_WORKFLOW, TEST_DEST_PACK, "clone_workflow"
        )
        clone_action_files(SOURCE_WORKFLOW, CLONE_WORKFLOW, TEST_DEST_PACK_PATH)
        # workflows directory created and asserting it exists
        self.assertTrue(os.path.exists(workflows_dir_path))


class CloneActionFilesBackupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        tests_config.parse_args()

    @classmethod
    def tearDownClass(cls):
        action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        workflow_files_path = os.path.join(action_files_path, "workflows")
        for file in os.listdir(action_files_path):
            if os.path.isfile(os.path.join(action_files_path, file)):
                os.remove(os.path.join(action_files_path, file))
        for file in os.listdir(workflow_files_path):
            if os.path.isfile(os.path.join(workflow_files_path, file)):
                os.remove(os.path.join(workflow_files_path, file))

    def test_temp_backup_restore_remove_action_files(self):
        CLONE_ACTION_1 = clone_action_db(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_1"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, CLONE_ACTION_1, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_1["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_1["entry_point"]
        temp_sub_dir = str(uuid.uuid4())

        # creating backup of dest action files at /tmp/<uuid>
        temp_backup_action_files(
            TEST_DEST_PACK_PATH,
            dest_action_metadata_file,
            dest_action_entry_point_file,
            temp_sub_dir,
        )
        temp_dir_path = "/tmp/%s" % temp_sub_dir
        self.assertTrue(os.path.isdir(temp_dir_path))
        temp_metadata_file_path = os.path.join(temp_dir_path, dest_action_metadata_file)
        temp_entry_point_file_path = os.path.join(
            temp_dir_path, "actions", dest_action_entry_point_file
        )
        # asserting backup files exists
        self.assertTrue(os.path.exists(temp_metadata_file_path))
        self.assertTrue(os.path.exists(temp_entry_point_file_path))

        # removing destination action files
        dest_action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        for file in os.listdir(dest_action_files_path):
            if os.path.isfile(os.path.join(dest_action_files_path, file)):
                os.remove(os.path.join(dest_action_files_path, file))
        dest_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, dest_action_metadata_file
        )
        dest_action_entry_point_file_path = os.path.join(
            TEST_DEST_PACK_PATH, "actions", dest_action_entry_point_file
        )
        # asserting destination action files doesn't exist
        self.assertFalse(os.path.isfile(dest_action_metadata_file_path))
        self.assertFalse(os.path.isfile(dest_action_entry_point_file_path))

        # restoring temp backed action files to destination
        restore_temp_action_files(
            TEST_DEST_PACK_PATH,
            dest_action_metadata_file,
            dest_action_entry_point_file,
            temp_sub_dir,
        )
        # asserting action files restored at destination
        self.assertTrue(os.path.isfile(dest_action_metadata_file_path))
        self.assertTrue(os.path.isfile(dest_action_entry_point_file_path))
        # asserting temp_dir and backed action files exits
        self.assertTrue(os.path.isdir(temp_dir_path))
        self.assertTrue(os.path.exists(temp_metadata_file_path))
        self.assertTrue(os.path.exists(temp_entry_point_file_path))

        # removing temp_dir and backed action files
        remove_temp_action_files(temp_sub_dir)
        # asserting temp_dir and backed action files doesn't exit
        self.assertFalse(os.path.isdir(temp_dir_path))
        self.assertFalse(os.path.exists(temp_metadata_file_path))
        self.assertFalse(os.path.exists(temp_entry_point_file_path))

    def test_exception_remove_temp_action_files(self):
        CLONE_ACTION_4 = clone_action_db(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_4"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, CLONE_ACTION_4, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_4["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_4["entry_point"]
        temp_sub_dir = str(uuid.uuid4())
        temp_backup_action_files(
            TEST_DEST_PACK_PATH,
            dest_action_metadata_file,
            dest_action_entry_point_file,
            temp_sub_dir,
        )
        temp_dir_path = "/tmp/%s" % temp_sub_dir
        self.assertTrue(os.path.isdir(temp_dir_path))
        expected_msg = (
            'The temporary directory "%s" could not be removed from disk, please check the logs '
            "or ask your StackStorm administrator to check and delete the temporary directory "
            "manually" % temp_dir_path
        )
        with mock.patch("shutil.rmtree") as mock_rmdir:
            mock_rmdir.side_effect = Exception
            with self.assertRaisesRegex(Exception, expected_msg):
                remove_temp_action_files(temp_sub_dir)

        remove_temp_action_files(temp_sub_dir)

    def test_permission_error_remove_temp_action_files(self):
        CLONE_ACTION_5 = clone_action_db(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_5"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_PYTHON_SCRIPT_RUNNER, CLONE_ACTION_5, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_5["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_5["entry_point"]
        temp_sub_dir = str(uuid.uuid4())
        temp_backup_action_files(
            TEST_DEST_PACK_PATH,
            dest_action_metadata_file,
            dest_action_entry_point_file,
            temp_sub_dir,
        )
        temp_dir_path = "/tmp/%s" % temp_sub_dir
        self.assertTrue(os.path.isdir(temp_dir_path))
        expected_msg = 'No permission to delete the "%s" directory' % temp_dir_path
        with mock.patch("shutil.rmtree") as mock_rmdir:
            mock_rmdir.side_effect = PermissionError
            with self.assertRaisesRegex(PermissionError, expected_msg):
                remove_temp_action_files(temp_sub_dir)

        remove_temp_action_files(temp_sub_dir)

    def test_exception_temp_backup_action_files(self):
        CLONE_ACTION_6 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_6"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, CLONE_ACTION_6, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_6["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_6["entry_point"]
        temp_sub_dir = str(uuid.uuid4())
        temp_dir_path = "/tmp/%s" % temp_sub_dir
        tmp_action_metadata_file_path = os.path.join(
            temp_dir_path, dest_action_metadata_file
        )
        expected_msg = (
            'Unable to copy file to "%s". Please check the logs or ask your '
            "administrator to clone the files manually." % tmp_action_metadata_file_path
        )
        with mock.patch("shutil.copy") as mock_copy:
            mock_copy.side_effect = Exception
            with self.assertRaisesRegex(Exception, expected_msg):
                temp_backup_action_files(
                    TEST_DEST_PACK_PATH,
                    dest_action_metadata_file,
                    dest_action_entry_point_file,
                    temp_sub_dir,
                )

        remove_temp_action_files(temp_sub_dir)

    def test_permission_error_temp_backup_action_files(self):
        CLONE_ACTION_7 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_7"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, CLONE_ACTION_7, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_7["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_7["entry_point"]
        temp_sub_dir = str(uuid.uuid4())
        temp_dir_path = "/tmp/%s" % temp_sub_dir
        tmp_action_metadata_file_path = os.path.join(
            temp_dir_path, dest_action_metadata_file
        )
        expected_msg = 'Unable to copy file to "%s".' % tmp_action_metadata_file_path
        with mock.patch("shutil.copy") as mock_copy:
            mock_copy.side_effect = PermissionError
            with self.assertRaisesRegex(PermissionError, expected_msg):
                temp_backup_action_files(
                    TEST_DEST_PACK_PATH,
                    dest_action_metadata_file,
                    dest_action_entry_point_file,
                    temp_sub_dir,
                )

        remove_temp_action_files(temp_sub_dir)

    def test_exception_restore_temp_action_files(self):
        CLONE_ACTION_8 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_8"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, CLONE_ACTION_8, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_8["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_8["entry_point"]
        dest_action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        for file in os.listdir(dest_action_files_path):
            if os.path.isfile(os.path.join(dest_action_files_path, file)):
                os.remove(os.path.join(dest_action_files_path, file))
        temp_sub_dir = str(uuid.uuid4())
        dest_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, dest_action_metadata_file
        )
        expected_msg = (
            'Unable to copy file to "%s". Please check the logs or ask your '
            "administrator to clone the files manually."
            % dest_action_metadata_file_path
        )
        with mock.patch("shutil.copy") as mock_copy:
            mock_copy.side_effect = Exception
            with self.assertRaisesRegex(Exception, expected_msg):
                restore_temp_action_files(
                    TEST_DEST_PACK_PATH,
                    dest_action_metadata_file,
                    dest_action_entry_point_file,
                    temp_sub_dir,
                )

        remove_temp_action_files(temp_sub_dir)

    def test_permission_error_restore_temp_action_files(self):
        CLONE_ACTION_9 = clone_action_db(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, TEST_DEST_PACK, "clone_action_9"
        )
        clone_action_files(
            SOURCE_ACTION_WITH_SHELL_SCRIPT_RUNNER, CLONE_ACTION_9, TEST_DEST_PACK_PATH
        )
        dest_action_metadata_file = CLONE_ACTION_9["metadata_file"]
        dest_action_entry_point_file = CLONE_ACTION_9["entry_point"]
        dest_action_files_path = os.path.join(TEST_DEST_PACK_PATH, "actions")
        for file in os.listdir(dest_action_files_path):
            if os.path.isfile(os.path.join(dest_action_files_path, file)):
                os.remove(os.path.join(dest_action_files_path, file))
        temp_sub_dir = str(uuid.uuid4())
        dest_action_metadata_file_path = os.path.join(
            TEST_DEST_PACK_PATH, dest_action_metadata_file
        )
        expected_msg = 'Unable to copy file to "%s".' % dest_action_metadata_file_path
        with mock.patch("shutil.copy") as mock_copy:
            mock_copy.side_effect = PermissionError
            with self.assertRaisesRegex(PermissionError, expected_msg):
                restore_temp_action_files(
                    TEST_DEST_PACK_PATH,
                    dest_action_metadata_file,
                    dest_action_entry_point_file,
                    temp_sub_dir,
                )

        remove_temp_action_files(temp_sub_dir)
