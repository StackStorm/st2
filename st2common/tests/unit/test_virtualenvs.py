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
import tempfile

import six
import mock
from oslo_config import cfg

from st2tests import config
from st2tests.base import CleanFilesTestCase
import st2common.util.virtualenvs as virtualenvs
from st2common.util.virtualenvs import install_requirement
from st2common.util.virtualenvs import install_requirements
from st2common.util.virtualenvs import setup_pack_virtualenv


__all__ = ["VirtualenvUtilsTestCase"]


# Note: We set base requirements to an empty list to speed up the tests
@mock.patch("st2common.util.virtualenvs.BASE_PACK_REQUIREMENTS", [])
class VirtualenvUtilsTestCase(CleanFilesTestCase):
    def setUp(self):
        super(VirtualenvUtilsTestCase, self).setUp()
        config.parse_args()

        dir_path = tempfile.mkdtemp()
        cfg.CONF.set_override(name="base_path", override=dir_path, group="system")

        self.base_path = dir_path
        self.virtualenvs_path = os.path.join(self.base_path, "virtualenvs/")

        # Make sure dir is deleted on tearDown
        self.to_delete_directories.append(self.base_path)

    def test_setup_pack_virtualenv_doesnt_exist_yet(self):
        # Test a fresh virtualenv creation
        pack_name = "dummy_pack_1"
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        # Note: This pack has no requirements
        setup_pack_virtualenv(
            pack_name=pack_name,
            update=False,
            include_pip=False,
            include_setuptools=False,
            include_wheel=False,
        )

        # Verify that virtualenv has been created
        self.assertVirtualenvExists(pack_virtualenv_dir)

    def test_setup_pack_virtualenv_already_exists(self):
        # Test a scenario where virtualenv already exists
        pack_name = "dummy_pack_1"
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        setup_pack_virtualenv(
            pack_name=pack_name,
            update=False,
            include_pip=False,
            include_setuptools=False,
            include_wheel=False,
        )

        # Verify that virtualenv has been created
        self.assertVirtualenvExists(pack_virtualenv_dir)

        # Re-create virtualenv
        setup_pack_virtualenv(
            pack_name=pack_name,
            update=False,
            include_pip=False,
            include_setuptools=False,
            include_wheel=False,
        )

        # Verify virtrualenv is still there
        self.assertVirtualenvExists(pack_virtualenv_dir)

    def test_setup_virtualenv_update(self):
        # Test a virtualenv update with pack which has requirements.txt
        pack_name = "dummy_pack_2"
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Create virtualenv
        setup_pack_virtualenv(
            pack_name=pack_name,
            update=False,
            include_setuptools=False,
            include_wheel=False,
        )

        # Verify that virtualenv has been created
        self.assertVirtualenvExists(pack_virtualenv_dir)

        # Update it
        setup_pack_virtualenv(
            pack_name=pack_name,
            update=True,
            include_setuptools=False,
            include_wheel=False,
        )

        # Verify virtrualenv is still there
        self.assertVirtualenvExists(pack_virtualenv_dir)

    def test_setup_virtualenv_invalid_dependency_in_requirements_file(self):
        pack_name = "pack_invalid_requirements"
        pack_virtualenv_dir = os.path.join(self.virtualenvs_path, pack_name)

        # Verify virtualenv directory doesn't exist
        self.assertFalse(os.path.exists(pack_virtualenv_dir))

        # Try to create virtualenv, assert that it fails
        try:
            setup_pack_virtualenv(
                pack_name=pack_name,
                update=False,
                include_setuptools=False,
                include_wheel=False,
            )
        except Exception as e:
            self.assertIn("Failed to install requirements from", six.text_type(e))
            self.assertTrue(
                "No matching distribution found for someinvalidname" in six.text_type(e)
            )
        else:
            self.fail("Exception not thrown")

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirement_without_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirement = "six>=1.9.0"
        install_requirement(pack_virtualenv_dir, requirement, proxy_config=None)
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "install",
                "six>=1.9.0",
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirement_with_http_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirement = "six>=1.9.0"
        proxy_config = {"http_proxy": "http://192.168.1.5:8080"}
        install_requirement(pack_virtualenv_dir, requirement, proxy_config=proxy_config)
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "http://192.168.1.5:8080",
                "install",
                "six>=1.9.0",
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirement_with_https_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirement = "six>=1.9.0"
        proxy_config = {
            "https_proxy": "https://192.168.1.5:8080",
            "proxy_ca_bundle_path": "/etc/ssl/certs/mitmproxy-ca.pem",
        }
        install_requirement(pack_virtualenv_dir, requirement, proxy_config=proxy_config)
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "https://192.168.1.5:8080",
                "--cert",
                "/etc/ssl/certs/mitmproxy-ca.pem",
                "install",
                "six>=1.9.0",
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirement_with_https_proxy_no_cert(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirement = "six>=1.9.0"
        proxy_config = {
            "https_proxy": "https://192.168.1.5:8080",
        }
        install_requirement(pack_virtualenv_dir, requirement, proxy_config=proxy_config)
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "https://192.168.1.5:8080",
                "install",
                "six>=1.9.0",
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirements_without_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirements_file_path = (
            "/opt/stackstorm/packs/dummy_pack_tests/requirements.txt"
        )
        install_requirements(
            pack_virtualenv_dir, requirements_file_path, proxy_config=None
        )
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "install",
                "-U",
                "-r",
                requirements_file_path,
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirements_with_http_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirements_file_path = (
            "/opt/stackstorm/packs/dummy_pack_tests/requirements.txt"
        )
        proxy_config = {"http_proxy": "http://192.168.1.5:8080"}
        install_requirements(
            pack_virtualenv_dir, requirements_file_path, proxy_config=proxy_config
        )
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "http://192.168.1.5:8080",
                "install",
                "-U",
                "-r",
                requirements_file_path,
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirements_with_https_proxy(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirements_file_path = (
            "/opt/stackstorm/packs/dummy_pack_tests/requirements.txt"
        )
        proxy_config = {
            "https_proxy": "https://192.168.1.5:8080",
            "proxy_ca_bundle_path": "/etc/ssl/certs/mitmproxy-ca.pem",
        }
        install_requirements(
            pack_virtualenv_dir, requirements_file_path, proxy_config=proxy_config
        )
        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "https://192.168.1.5:8080",
                "--cert",
                "/etc/ssl/certs/mitmproxy-ca.pem",
                "install",
                "-U",
                "-r",
                requirements_file_path,
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    @mock.patch.object(
        virtualenvs, "run_command", mock.MagicMock(return_value=(0, "", ""))
    )
    @mock.patch.object(
        virtualenvs, "get_env_for_subprocess_command", mock.MagicMock(return_value={})
    )
    def test_install_requirements_with_https_proxy_no_cert(self):
        pack_virtualenv_dir = "/opt/stackstorm/virtualenvs/dummy_pack_tests/"
        requirements_file_path = (
            "/opt/stackstorm/packs/dummy_pack_tests/requirements.txt"
        )
        proxy_config = {
            "https_proxy": "https://192.168.1.5:8080",
        }
        install_requirements(
            pack_virtualenv_dir, requirements_file_path, proxy_config=proxy_config
        )

        expected_args = {
            "cmd": [
                "/opt/stackstorm/virtualenvs/dummy_pack_tests/bin/pip",
                "--proxy",
                "https://192.168.1.5:8080",
                "install",
                "-U",
                "-r",
                requirements_file_path,
            ],
            "env": {},
        }
        virtualenvs.run_command.assert_called_once_with(**expected_args)

    def assertVirtualenvExists(self, virtualenv_dir):
        self.assertTrue(os.path.exists(virtualenv_dir))
        self.assertTrue(os.path.isdir(virtualenv_dir))
        self.assertTrue(os.path.isdir(os.path.join(virtualenv_dir, "bin/")))

        return True
