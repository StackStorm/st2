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
import tempfile

from oslo_config import cfg

from st2tests import config
from st2tests.base import CleanFilesTestCase
from st2common.util.virtualenvs import setup_pack_virtualenv


class VirtualenvUtilsTestCase(CleanFilesTestCase):
    def setUp(self):
        super(VirtualenvUtilsTestCase, self).setUp()
        config.parse_args()

        dir_path = tempfile.mkdtemp()
        cfg.CONF.set_override(name='base_path', override=dir_path, group='system')

        self.base_path = dir_path
        self.virtualenvs_path = os.path.join(self.base_path, 'virtualenvs/')

        # Make sure dir is deleted on tearDown
        self.to_delete_directories.append(self.base_path)

    def test_setup_pack_virtualenv_doesnt_exist_yet(self):
        # Test a fresh virtualenv creation
        pack_name = 'dummy_pack_1'
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        # Note: This pack has no requirements
        setup_pack_virtualenv(pack_name=pack_name, update=False)

        # Verify that virtualenv has been created
        self.assertVirtulenvExists(pack_virtualenv_dir)

    def test_setup_pack_virtualenv_already_exists(self):
        # Test a scenario where virtualenv already exists
        pack_name = 'dummy_pack_1'
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        setup_pack_virtualenv(pack_name=pack_name, update=False)

        # Verify that virtualenv has been created
        self.assertVirtulenvExists(pack_virtualenv_dir)

        # Re-create virtualenv
        setup_pack_virtualenv(pack_name=pack_name, update=False)

        # Verify virtrualenv is still there
        self.assertVirtulenvExists(pack_virtualenv_dir)

    def test_setup_virtualenv_update(self):
        # Test a virtualenv update with pack which has requirements.txt
        pack_name = 'dummy_pack_2'
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        setup_pack_virtualenv(pack_name=pack_name, update=False)

        # Verify that virtualenv has been created
        self.assertVirtulenvExists(pack_virtualenv_dir)

        # Update it
        setup_pack_virtualenv(pack_name=pack_name, update=True)

        # Verify virtrualenv is still there
        self.assertVirtulenvExists(pack_virtualenv_dir)

    def test_setup_virtualenv_invalid_dependency_in_requirements_file(self):
        pack_name = 'pack_invalid_requirements'
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Try to create virtualenv, assert that it fails
        try:
            setup_pack_virtualenv(pack_name=pack_name, update=False)
        except Exception as e:
            self.assertTrue('Failed to install requirements from' in str(e))
            self.assertTrue('No matching distribution found for someinvalidname' in str(e))
        else:
            self.fail('Exception not thrown')

    def assertVirtulenvExists(self, virtualenv_dir):
        self.assertTrue(os.path.exists(virtualenv_dir))
        self.assertTrue(os.path.isdir(virtualenv_dir))
        self.assertTrue(os.path.isdir(os.path.join(virtualenv_dir, 'bin/')))

        return True
