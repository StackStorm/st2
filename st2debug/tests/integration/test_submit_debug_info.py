# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import tarfile
import tempfile

import mock
import unittest2
from distutils.spawn import find_executable

from st2tests.base import CleanFilesTestCase
from st2debug.cmd.submit_debug_info import create_archive
from st2debug.cmd.submit_debug_info import encrypt_archive
import st2debug.cmd.submit_debug_info

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(BASE_DIR, 'fixtures')
GPG_INSTALLED = find_executable('gpg') is not None
SUBMIT_DEBUG_YAML_FILE = os.path.join(FIXTURES_DIR, 'submit-debug-info.yaml')


@unittest2.skipIf(not GPG_INSTALLED, 'gpg binary not available')
class SubmitDebugInfoTestCase(CleanFilesTestCase):
    def setUp(self):
        super(SubmitDebugInfoTestCase, self).setUp()

        # Mock paths so we include mock data
        logs_dir = os.path.join(FIXTURES_DIR, 'logs/')
        st2debug.cmd.submit_debug_info.ST2_LOG_FILES_PATH = logs_dir + '*.log'
        st2debug.cmd.submit_debug_info.LOG_FILE_PATHS = [
            st2debug.cmd.submit_debug_info.ST2_LOG_FILES_PATH
        ]

        configs_dir = os.path.join(FIXTURES_DIR, 'configs/')
        st2debug.cmd.submit_debug_info.ST2_CONFIG_FILE_PATH = os.path.join(configs_dir, 'st2.conf')
        st2debug.cmd.submit_debug_info.MISTRAL_CONFIG_FILE_PATH = os.path.join(configs_dir,
                                                                               'mistral.conf')
        st2debug.cmd.submit_debug_info.CONFIG_FILE_PATHS = [
            st2debug.cmd.submit_debug_info.ST2_CONFIG_FILE_PATH,
            st2debug.cmd.submit_debug_info.MISTRAL_CONFIG_FILE_PATH
        ]

        # Mock get_packs_base_paths
        content_dir = os.path.join(FIXTURES_DIR, 'content/')
        return_value = [content_dir]
        st2debug.cmd.submit_debug_info.get_packs_base_paths = mock.Mock()
        st2debug.cmd.submit_debug_info.get_packs_base_paths.return_value = return_value

    def _verify_archive(self, archive_path, extract_path, required_directories):
        # Verify archive has been created
        self.assertTrue(os.path.isfile(archive_path))
        self.to_delete_files.append(archive_path)

        self.to_delete_directories.append(extract_path)
        self._extract_archive(archive_path=archive_path, extract_path=extract_path)

        for directory_name in required_directories:
            full_path = os.path.join(extract_path, directory_name)
            self.assertTrue(os.path.isdir(full_path))

        # Verify system info file has ben created
        full_path = os.path.join(extract_path, 'system_info.yaml')
        self.assertTrue(os.path.isfile(full_path))

        # Verify logs have been copied
        logs_path = os.path.join(extract_path, 'logs')
        log_files = os.listdir(logs_path)
        self.assertTrue(len(log_files), 2)

        # Verify configs have been copied
        st2_config_path = os.path.join(extract_path, 'configs', 'st2.conf')
        mistral_config_path = os.path.join(extract_path, 'configs', 'mistral.conf')

        self.assertTrue(os.path.isfile(st2_config_path))
        self.assertTrue(os.path.isfile(mistral_config_path))

        # Verify packs have been copied
        content_path = os.path.join(extract_path, 'content/dir-1')
        pack_directories = os.listdir(content_path)
        self.assertEqual(len(pack_directories), 1)

        # Verify sensitive data has been masked in the configs
        with open(st2_config_path, 'r') as fp:
            st2_config_content = fp.read()

        with open(mistral_config_path, 'r') as fp:
            mistral_config_content = fp.read()

        self.assertTrue('ponies' not in st2_config_content)
        self.assertTrue('username = **removed**' in st2_config_content)
        self.assertTrue('password = **removed**' in st2_config_content)
        self.assertTrue('url = **removed**' in st2_config_content)

        self.assertTrue('StackStorm' not in mistral_config_content)
        self.assertTrue('connection = **removed**' in mistral_config_content)

        # Very config.yaml has been removed from the content pack directories
        pack_dir = os.path.join(content_path, 'twilio')
        config_path = os.path.join(pack_dir, 'config.yaml')

        self.assertTrue(os.path.isdir(pack_dir))
        self.assertTrue(not os.path.exists(config_path))

    def test_create_archive_include_all(self):
        archive_path = create_archive(include_logs=True, include_configs=True,
                                      include_content=True,
                                      include_system_info=True)
        extract_path = tempfile.mkdtemp()
        self._verify_archive(archive_path=archive_path,
                             extract_path=extract_path,
                             required_directories=['logs', 'configs', 'content'])

    def test_create_archive_include_all_with_config_option(self):
        # Load the submit debug info yaml file
        st2debug.cmd.submit_debug_info.load_config_yaml_file(SUBMIT_DEBUG_YAML_FILE)
        archive_path = create_archive(include_logs=True, include_configs=True,
                                      include_content=True,
                                      include_system_info=True,
                                      include_shell_commands=True,
                                      config_yaml=SUBMIT_DEBUG_YAML_FILE)
        extract_path = tempfile.mkdtemp()
        self._verify_archive(archive_path=archive_path,
                             extract_path=extract_path,
                             required_directories=['logs', 'configs', 'content', 'commands'])

        # Verify commands output have been copied
        commands_path = os.path.join(extract_path, 'commands')
        command_files = os.listdir(commands_path)
        self.assertTrue(len(command_files), 1)

    def test_create_archive_exclusion(self):
        # Verify only system info file is included
        archive_path = create_archive(include_logs=False, include_configs=False,
                                      include_content=False,
                                      include_system_info=True)

        # Verify archive has been created
        self.assertTrue(os.path.isfile(archive_path))
        self.to_delete_files.append(archive_path)

        extract_path = tempfile.mkdtemp()
        self.to_delete_directories.append(extract_path)
        self._extract_archive(archive_path=archive_path, extract_path=extract_path)

        # Verify system info file is there and other directories are empty
        directories = ['logs', 'configs', 'content']

        for directory_name in directories:
            full_path = os.path.join(extract_path, directory_name)
            files = os.listdir(full_path)
            self.assertEqual(len(files), 0)

        full_path = os.path.join(extract_path, 'system_info.yaml')
        self.assertTrue(os.path.isfile(full_path))

    def test_encrypt_archive(self):
        plaintext_archive_path = create_archive(include_logs=True, include_configs=True,
                                                include_content=True,
                                                include_system_info=True)
        plaintext_archive_size = os.stat(plaintext_archive_path).st_size

        encrypted_archive_path = encrypt_archive(archive_file_path=plaintext_archive_path)
        encrypt_archive_size = os.stat(encrypted_archive_path).st_size

        self.assertTrue(os.path.isfile(encrypted_archive_path))
        self.assertTrue(encrypt_archive_size > plaintext_archive_size)

        self.assertRaises(Exception, archive_path=encrypted_archive_path,
                          extract_path='/tmp')

    def test_encrypt_archive_with_custom_gpg_key(self):
        # Load the submit debug info yaml file
        st2debug.cmd.submit_debug_info.load_config_yaml_file(SUBMIT_DEBUG_YAML_FILE)

        plaintext_archive_path = create_archive(include_logs=True, include_configs=True,
                                                include_content=True,
                                                include_system_info=True,
                                                include_shell_commands=True,
                                                config_yaml=SUBMIT_DEBUG_YAML_FILE)

        plaintext_archive_size = os.stat(plaintext_archive_path).st_size

        encrypted_archive_path = encrypt_archive(archive_file_path=plaintext_archive_path)
        encrypt_archive_size = os.stat(encrypted_archive_path).st_size

        self.assertTrue(os.path.isfile(encrypted_archive_path))
        self.assertTrue(encrypt_archive_size > plaintext_archive_size)

        self.assertRaises(Exception, archive_path=encrypted_archive_path,
                          extract_path='/tmp')

    def _extract_archive(self, archive_path, extract_path):
        with tarfile.open(archive_path) as tar:
            tar.extractall(path=extract_path)
