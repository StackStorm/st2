#!/usr/bin/env python

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

import mock

from st2tests.base import BaseActionTestCase

from pack_mgmt.get_pack_dependencies import GetPackDependencies

UNINSTALLED_PACK = 'uninstalled_pack'
UNINSTALLED_PACK_URL = 'https://github.com/StackStorm-Exchange/stackstorm-' + UNINSTALLED_PACK\
                       + '.git'
UNINSTALLED_PRIVATE_PACK_URL = 'https://github.com/privaterepo/' + UNINSTALLED_PACK + '.git=v4.5.0'
UNINSTALLED_LOCAL_PACK = 'file:///opt/pack_dir/' + UNINSTALLED_PACK + '=v4.5.0'

DOWNLOADED_OR_INSTALLED_PACK_METAdATA = {
    # No dependencies.
    "no_dependencies": {
        "version": "0.4.0",
        "name": "no_dependencies",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-no_dependencies",
        "author": "st2-dev",
        "keywords": ["some", "search", "another", "terms"],
        "email": "info@stackstorm.com",
        "description": "st2 pack to test package management pipeline",
    },
    # One uninstalled and one installed dependency packs.
    "test2": {
        "version": "0.5.0",
        "name": "test2",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test2",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
        "dependencies": [
            UNINSTALLED_PACK, "test3"
        ]
    },
    # One uninstalled, one installed and one conflict dependency packs.
    "test3": {
        "version": "0.6.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test3",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test3",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
        "dependencies": [
            UNINSTALLED_PACK, "test2=v0.4.0", "test4=v0.7.0"
        ]
    },
    # One uninstalled, one installed and one conflict with StackStorm Exchange urls.
    "test4": {
        "version": "0.7.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test4",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test4",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
        "dependencies": [
            UNINSTALLED_PACK_URL,
            "https://github.com/StackStorm-Exchange/stackstorm-test2=v0.4.0",
            "https://github.com/StackStorm-Exchange/stackstorm-test5.git"
        ]
    },
    # One uninstalled, one installed and one conflict private urls.
    "test5": {
        "version": "0.8.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test3",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test5",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
        "dependencies": [
            UNINSTALLED_PRIVATE_PACK_URL,
            "https://github.com/privaterepo/test4.git=v0.5.0",
            "https://github.com/privaterepo/test6.git"
        ]
    },
    # One uninstalled, one installed and one conflict local files.
    "test6": {
        "version": "0.9.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test3",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test6",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
        "dependencies": [
            UNINSTALLED_LOCAL_PACK,
            "file:///opt/pack_dir/test2=v0.7.0",
            "file:///opt/some_dir/test5=v0.8.0"
        ]
    }
}


def mock_get_dependency_list(pack):
    """
    Mock get_dependency_list function which return dependencies list
    """
    dependencies = None

    if pack in DOWNLOADED_OR_INSTALLED_PACK_METAdATA:
        metadata = DOWNLOADED_OR_INSTALLED_PACK_METAdATA[pack]
        dependencies = metadata.get('dependencies', None)

    return dependencies


def mock_get_pack_version(pack):
    """
    Mock get_pack_version function which return mocked pack version
    """
    version = None

    if pack in DOWNLOADED_OR_INSTALLED_PACK_METAdATA:
        metadata = DOWNLOADED_OR_INSTALLED_PACK_METAdATA[pack]
        version = metadata.get('version', None)

    return version


@mock.patch('pack_mgmt.get_pack_dependencies.get_dependency_list', mock_get_dependency_list)
@mock.patch('pack_mgmt.get_pack_dependencies.get_pack_version', mock_get_pack_version)
class GetPackDependenciesTestCase(BaseActionTestCase):
    action_cls = GetPackDependencies

    def setUp(self):
        super(GetPackDependenciesTestCase, self).setUp()

    def test_run_get_pack_dependencies_with_nested_zero_value(self):
        action = self.get_action_instance()
        packs_status = {"test": "Success."}
        nested = 0

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result, {})

    def test_run_get_pack_dependencies_with_empty_packs_status(self):
        action = self.get_action_instance()
        packs_status = None
        nested = 3

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result, {})

    def test_run_get_pack_dependencies_with_failed_packs_status(self):
        action = self.get_action_instance()
        packs_status = {"test3": "Failed."}
        nested = 2

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [])
        self.assertEqual(result['conflict_list'], [])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies_with_failed_and_succeeded_packs_status(self):
        action = self.get_action_instance()
        packs_status = {"test3": "Failed.", "test2": "Success."}
        nested = 2

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [UNINSTALLED_PACK])
        self.assertEqual(result['conflict_list'], [])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies_with_no_dependency(self):
        action = self.get_action_instance()
        packs_status = {"no_dependencies": "Success."}
        nested = 3

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [])
        self.assertEqual(result['conflict_list'], [])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies(self):
        action = self.get_action_instance()
        packs_status = {"test3": "Success.", "test2": "Success."}
        nested = 1

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [UNINSTALLED_PACK])
        self.assertEqual(result['conflict_list'], ['test2=v0.4.0'])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies_with_stackstorm_exchange_url(self):
        action = self.get_action_instance()
        packs_status = {"test4": "Success."}
        nested = 3

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [UNINSTALLED_PACK_URL])
        self.assertEqual(result['conflict_list'],
                         ['https://github.com/StackStorm-Exchange/stackstorm-test2=v0.4.0'])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies_with_private_url(self):
        action = self.get_action_instance()
        packs_status = {"test5": "Success."}
        nested = 3

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [UNINSTALLED_PRIVATE_PACK_URL])
        self.assertEqual(result['conflict_list'],
                         ['https://github.com/privaterepo/test4.git=v0.5.0'])
        self.assertEqual(result['nested'], nested - 1)

    def test_run_get_pack_dependencies_with_local_file(self):
        action = self.get_action_instance()
        packs_status = {"test6": "Success."}
        nested = 3

        result = action.run(packs_status=packs_status, nested=nested)
        self.assertEqual(result['dependency_list'], [UNINSTALLED_LOCAL_PACK])
        self.assertEqual(result['conflict_list'], ["file:///opt/pack_dir/test2=v0.7.0"])
        self.assertEqual(result['nested'], nested - 1)
