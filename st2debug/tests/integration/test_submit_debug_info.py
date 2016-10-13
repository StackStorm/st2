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
from st2debug.cmd.submit_debug_info import DebugInfoCollector
import st2debug.cmd.submit_debug_info
from st2debug.constants import GPG_KEY
from st2debug.constants import GPG_KEY_FINGERPRINT
from st2debug.constants import S3_BUCKET_URL

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
        st2debug.cmd.submit_debug_info.LOG_FILE_PATHS = [logs_dir + '*.log']

        configs_dir = os.path.join(FIXTURES_DIR, 'configs/')
        st2debug.cmd.submit_debug_info.ST2_CONFIG_FILE_PATH = os.path.join(configs_dir, 'st2.conf')
        st2debug.cmd.submit_debug_info.MISTRAL_CONFIG_FILE_PATH = os.path.join(configs_dir,
                                                                               'mistral.conf')

        # Mock get_packs_base_paths
        content_dir = os.path.join(FIXTURES_DIR, 'content/')
        return_value = [content_dir]
        st2debug.cmd.submit_debug_info.get_packs_base_paths = mock.Mock()
        st2debug.cmd.submit_debug_info.get_packs_base_paths.return_value = return_value

    def test_create_archive_include_all(self):
        debug_collector = DebugInfoCollector(include_logs=True, include_configs=True,
                                             include_content=True,
                                             include_system_info=True)
        archive_path = debug_collector.create_archive()
        extract_path = tempfile.mkdtemp()
        self._verify_archive(archive_path=archive_path,
                             extract_path=extract_path,
                             required_directories=['logs', 'configs', 'content'])

    def test_create_archive_deletes_temp_dir(self):
        debug_collector = DebugInfoCollector(include_logs=True, include_configs=True,
                                             include_content=True,
                                             include_system_info=True)
        archive_path = debug_collector.create_archive()
        self.to_delete_files.append(archive_path)

        self.assertTrue(debug_collector._temp_dir_path)
        self.assertTrue(not os.path.exists(debug_collector._temp_dir_path))

    def test_config_option_overrides_defaults(self):
        config = {
            'log_file_paths': [
                'log/path/1',
                'log/path/1'
            ],
            'st2_config_file_path': 'st2/config/path',
            'mistral_config_file_path': 'mistral/config/path',
            's3_bucket_url': 'my_s3_url',
            'gpg_key_fingerprint': 'my_gpg_fingerprint',
            'gpg_key': 'my_gpg_key',
            'shell_commands': [
                'command 1',
                'command 2'
            ],
            'company_name': 'MyCompany'
        }

        debug_collector = DebugInfoCollector(include_logs=True,
                                             include_configs=True,
                                             include_content=True,
                                             include_system_info=True,
                                             config_file=config)
        self.assertEqual(debug_collector.log_file_paths, ['log/path/1', 'log/path/1'])
        self.assertEqual(debug_collector.st2_config_file_path, 'st2/config/path')
        self.assertEqual(debug_collector.st2_config_file_name, 'path')
        self.assertEqual(debug_collector.mistral_config_file_path, 'mistral/config/path')
        self.assertEqual(debug_collector.mistral_config_file_name, 'path')
        self.assertEqual(debug_collector.s3_bucket_url, 'my_s3_url')
        self.assertEqual(debug_collector.gpg_key, 'my_gpg_key')
        self.assertEqual(debug_collector.gpg_key_fingerprint, 'my_gpg_fingerprint')
        self.assertEqual(debug_collector.shell_commands, ['command 1', 'command 2'])
        self.assertEqual(debug_collector.company_name, 'MyCompany')

    def test_create_archive_include_all_with_config_option(self):
        yaml_config = self._get_yaml_config()
        debug_collector = DebugInfoCollector(include_logs=True, include_configs=True,
                                             include_content=True,
                                             include_system_info=True,
                                             include_shell_commands=True,
                                             config_file=yaml_config)
        archive_path = debug_collector.create_archive()
        extract_path = tempfile.mkdtemp()
        self._verify_archive(archive_path=archive_path,
                             extract_path=extract_path,
                             required_directories=['logs', 'configs', 'content', 'commands'])

        # Verify commands output have been copied
        commands_path = os.path.join(extract_path, 'commands')
        command_files = os.listdir(commands_path)
        self.assertTrue(len(command_files), 2)

        # Verify command output file names
        self.assertTrue('echofoo.txt' in command_files)
        self.assertTrue('echobar12.txt' in command_files)

        # Verify file contents
        with open(os.path.join(commands_path, 'echofoo.txt')) as f:
            expected_content = '[BEGIN STDOUT]\nfoo\n[END STDOUT]\n[BEGIN STDERR]\n[END STDERR]'
            self.assertEqual(expected_content, f.read())

        with open(os.path.join(commands_path, 'echobar12.txt')) as f:
            expected_content = '[BEGIN STDOUT]\n[END STDOUT]\n[BEGIN STDERR]\nbar\n[END STDERR]'
            self.assertEqual(expected_content, f.read())

    def test_create_archive_exclusion(self):
        # Verify only system info file is included
        debug_collector = DebugInfoCollector(include_logs=False, include_configs=False,
                                             include_content=False, include_system_info=True)
        archive_path = debug_collector.create_archive()

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
        debug_collector = DebugInfoCollector(include_logs=True, include_configs=True,
                                             include_content=True,
                                             include_system_info=True)
        plaintext_archive_path = debug_collector.create_archive()
        plaintext_archive_size = os.stat(plaintext_archive_path).st_size

        encrypted_archive_path = debug_collector.encrypt_archive(
            archive_file_path=plaintext_archive_path)
        encrypt_archive_size = os.stat(encrypted_archive_path).st_size

        self.assertTrue(os.path.isfile(encrypted_archive_path))
        self.assertTrue(encrypt_archive_size > plaintext_archive_size)

        self.assertRaises(Exception, archive_path=encrypted_archive_path,
                          extract_path='/tmp')

    def test_encrypt_archive_with_custom_gpg_key(self):
        yaml_config = self._get_yaml_config()
        debug_collector = DebugInfoCollector(include_logs=True, include_configs=True,
                                             include_content=True,
                                             include_system_info=True,
                                             include_shell_commands=True,
                                             config_file=yaml_config)
        plaintext_archive_path = debug_collector.create_archive()

        plaintext_archive_size = os.stat(plaintext_archive_path).st_size

        encrypted_archive_path = debug_collector.encrypt_archive(
            archive_file_path=plaintext_archive_path)
        encrypt_archive_size = os.stat(encrypted_archive_path).st_size

        self.assertTrue(os.path.isfile(encrypted_archive_path))
        self.assertTrue(encrypt_archive_size > plaintext_archive_size)

        self.assertRaises(Exception, archive_path=encrypted_archive_path,
                          extract_path='/tmp')

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

    def _get_yaml_config(self):
        return {
            'log_file_paths': [
                os.path.join(FIXTURES_DIR, 'logs/st2*.log')
            ],
            'st2_config_file_path': os.path.join(FIXTURES_DIR, 'configs/st2.conf'),
            'mistral_config_file_path': os.path.join(FIXTURES_DIR, 'configs/mistral.conf'),
            's3_bucket_url': S3_BUCKET_URL,
            'gpg_key_fingerprint': GPG_KEY_FINGERPRINT,
            'gpg_key': GPG_KEY,
            'shell_commands': [
                'echo foo',
                'echo bar 1>&2'
            ],
            'company_name': 'MyCompany'
        }

    def _extract_archive(self, archive_path, extract_path):
        with tarfile.open(archive_path) as tar:
            tar.extractall(path=extract_path)
