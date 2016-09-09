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

from st2tests.base import IntegrationTestCase
from st2common.util.shell import run_command
from st2tests import config as test_config
from st2tests.fixturesloader import get_fixtures_packs_base_path


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(BASE_DIR, '../../bin/st2-register-content')
SCRIPT_PATH = os.path.abspath(SCRIPT_PATH)

BASE_CMD_ARGS = [SCRIPT_PATH, '--config-file=conf/st2.tests.conf', '-v']
BASE_REGISTER_ACTIONS_CMD_ARGS = BASE_CMD_ARGS + ['--register-actions']


class ContentRegisterScripTestCase(IntegrationTestCase):
    def setUp(self):
        super(ContentRegisterScripTestCase, self).setUp()
        test_config.parse_args()

    def test_register_from_pack_success(self):
        pack_dir = os.path.join(get_fixtures_packs_base_path(), 'dummy_pack_1')

        cmd = BASE_REGISTER_ACTIONS_CMD_ARGS + ['--register-pack=%s' % (pack_dir)]
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('Registered 1 actions.' in stderr)
        self.assertEqual(exit_code, 0)

    def test_register_from_pack_fail_on_failure_pack_dir_doesnt_exist(self):
        # No fail on failure flag, should succeed
        pack_dir = 'doesntexistblah'
        cmd = BASE_REGISTER_ACTIONS_CMD_ARGS + ['--register-pack=%s' % (pack_dir),
                                                '--register-no-fail-on-failure']
        exit_code, _, _ = run_command(cmd=cmd)
        self.assertEqual(exit_code, 0)

        # Fail on failure, should fail
        cmd = BASE_REGISTER_ACTIONS_CMD_ARGS + ['--register-pack=%s' % (pack_dir),
                                                '--register-fail-on-failure']
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('Directory "doesntexistblah" doesn\'t exist' in stderr)
        self.assertEqual(exit_code, 1)

    def test_register_from_pack_action_metadata_fails_validation(self):
        # No fail on failure flag, should succeed
        pack_dir = os.path.join(get_fixtures_packs_base_path(), 'dummy_pack_4')
        cmd = BASE_REGISTER_ACTIONS_CMD_ARGS + ['--register-pack=%s' % (pack_dir),
                                                '--register-no-fail-on-failure']
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('Registered 0 actions.' in stderr)
        self.assertEqual(exit_code, 0)

        # Fail on failure, should fail
        pack_dir = os.path.join(get_fixtures_packs_base_path(), 'dummy_pack_4')
        cmd = BASE_REGISTER_ACTIONS_CMD_ARGS + ['--register-pack=%s' % (pack_dir),
                                                '--register-fail-on-failure']
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('object has no attribute \'get\'' in stderr)
        self.assertEqual(exit_code, 1)

    def test_register_from_packs_doesnt_throw_on_missing_pack_resource_folder(self):
        # dummy_pack_4 only has actions folder, make sure it doesn't throw when
        # sensors and other resource folders are missing

        # Note: We want to use a different config which sets fixtures/packs_1/
        # dir as packs_base_paths
        cmd = [SCRIPT_PATH, '--config-file=conf/st2.tests1.conf', '-v', '--register-sensors']
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('Registered 0 sensors.' in stderr)
        self.assertEqual(exit_code, 0)

        cmd = [SCRIPT_PATH, '--config-file=conf/st2.tests1.conf', '-v', '--register-all',
               '--register-no-fail-on-failure']
        exit_code, _, stderr = run_command(cmd=cmd)
        self.assertTrue('Registered 0 actions.' in stderr)
        self.assertTrue('Registered 0 sensors.' in stderr)
        self.assertTrue('Registered 0 rules.' in stderr)
        self.assertEqual(exit_code, 0)

    def test_register_all_and_register_setup_virtualenvs(self):
        # Verify that --register-all works in combinations with --register-setuo-virtualenvs
        cmd = BASE_CMD_ARGS + ['--register-all', '--register-setup-virtualenvs',
                               '--register-no-fail-on-failure']
        exit_code, stdout, stderr = run_command(cmd=cmd)
        self.assertTrue('Registering actions' in stderr)
        self.assertTrue('Registering rules' in stderr)
        self.assertTrue('Setup virtualenv for 6 pack(s)' in stderr)
        self.assertEqual(exit_code, 0)

    def test_register_setup_virtualenvs(self):
        # Single pack
        pack_dir = os.path.join(get_fixtures_packs_base_path(), 'dummy_pack_1')

        cmd = BASE_CMD_ARGS + ['--register-pack=%s' % (pack_dir), '--register-setup-virtualenvs',
                               '--register-no-fail-on-failure']
        exit_code, stdout, stderr = run_command(cmd=cmd)

        self.assertTrue('Setting up virtualenv for pack "dummy_pack_1"' in stderr)
        self.assertTrue('Setup virtualenv for 1 pack(s)' in stderr)
        self.assertEqual(exit_code, 0)

        # All packs
        cmd = BASE_CMD_ARGS + ['--register-setup-virtualenvs', '--register-no-fail-on-failure']
        exit_code, stdout, stderr = run_command(cmd=cmd)
        self.assertTrue('Setup virtualenv for 6 pack(s)' in stderr)
        self.assertEqual(exit_code, 0)
