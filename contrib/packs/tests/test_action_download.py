#!/usr/bin/env python

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
import mock
import shutil
import tempfile
import hashlib

from lockfile import LockFile
from lockfile import LockTimeout
from git.repo import Repo
from gitdb.exc import BadName
from st2common.services import packs as pack_service
from st2tests.base import BaseActionTestCase

import pack_mgmt.download
from pack_mgmt.download import DownloadGitRepoAction

PACK_INDEX = {
    "test": {
        "version": "0.4.0",
        "name": "test",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test",
        "author": "st2-dev",
        "keywords": ["some", "search", "another", "terms"],
        "email": "info@stackstorm.com",
        "description": "st2 pack to test package management pipeline"
    },
    "test2": {
        "version": "0.5.0",
        "name": "test2",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test2",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline"
    },
    "test3": {
        "version": "0.5.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test3",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test3",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline"
    }
}


@mock.patch.object(pack_service, 'fetch_pack_index', mock.MagicMock(return_value=(PACK_INDEX, {})))
class DownloadGitRepoActionTestCase(BaseActionTestCase):
    action_cls = DownloadGitRepoAction

    def setUp(self):
        super(DownloadGitRepoActionTestCase, self).setUp()

        clone_from = mock.patch.object(Repo, 'clone_from')

        self.addCleanup(clone_from.stop)
        self.clone_from = clone_from.start()

        expand_user = mock.patch.object(os.path, 'expanduser',
                                        mock.MagicMock(return_value=tempfile.mkdtemp()))

        self.addCleanup(expand_user.stop)
        self.expand_user = expand_user.start()

        self.repo_base = tempfile.mkdtemp()

        self.repo_instance = mock.MagicMock()

        def side_effect(url, to_path, **kwargs):
            # Since we have no way to pass pack name here, we would have to derive it from repo url
            fixture_name = url.split('/')[-1]
            fixture_path = os.path.join(self._get_base_pack_path(), 'tests/fixtures', fixture_name)
            shutil.copytree(fixture_path, to_path)
            return self.repo_instance

        self.clone_from.side_effect = side_effect

    def tearDown(self):
        shutil.rmtree(self.repo_base)
        shutil.rmtree(self.expand_user())

    def test_run_pack_download(self):
        action = self.get_action_instance()
        result = action.run(packs=['test'], abs_repo_base=self.repo_base)
        temp_dir = hashlib.md5(PACK_INDEX['test']['repo_url']).hexdigest()

        self.assertEqual(result, {'test': 'Success.'})
        self.clone_from.assert_called_once_with(PACK_INDEX['test']['repo_url'],
                                                os.path.join(os.path.expanduser('~'), temp_dir))
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, 'test/pack.yaml')))

    def test_run_pack_download_existing_pack(self):
        action = self.get_action_instance()
        action.run(packs=['test'], abs_repo_base=self.repo_base)
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, 'test/pack.yaml')))

        result = action.run(packs=['test'], abs_repo_base=self.repo_base)

        self.assertEqual(result, {'test': 'Success.'})

    def test_run_pack_download_multiple_packs(self):
        action = self.get_action_instance()
        result = action.run(packs=['test', 'test2'], abs_repo_base=self.repo_base)
        temp_dirs = [
            hashlib.md5(PACK_INDEX['test']['repo_url']).hexdigest(),
            hashlib.md5(PACK_INDEX['test2']['repo_url']).hexdigest()
        ]

        self.assertEqual(result, {'test': 'Success.', 'test2': 'Success.'})
        self.clone_from.assert_any_call(PACK_INDEX['test']['repo_url'],
                                        os.path.join(os.path.expanduser('~'), temp_dirs[0]))
        self.clone_from.assert_any_call(PACK_INDEX['test2']['repo_url'],
                                        os.path.join(os.path.expanduser('~'), temp_dirs[1]))
        self.assertEqual(self.clone_from.call_count, 2)
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, 'test/pack.yaml')))
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, 'test2/pack.yaml')))

    @mock.patch.object(Repo, 'clone_from')
    def test_run_pack_download_error(self, clone_from):
        clone_from.side_effect = Exception('Something went terribly wrong during the clone')

        action = self.get_action_instance()
        self.assertRaises(Exception, action.run, packs=['test'], abs_repo_base=self.repo_base)

    def test_run_pack_download_no_tag(self):
        self.repo_instance.commit.side_effect = BadName

        action = self.get_action_instance()
        self.assertRaises(ValueError, action.run, packs=['test=1.2.3'],
                          abs_repo_base=self.repo_base)

    def test_run_pack_lock_is_already_acquired(self):
        action = self.get_action_instance()
        temp_dir = hashlib.md5(PACK_INDEX['test']['repo_url']).hexdigest()

        original_acquire = LockFile.acquire

        def mock_acquire(self, timeout=None):
            original_acquire(self, timeout=0.1)

        LockFile.acquire = mock_acquire

        try:
            lock_file = LockFile('/tmp/%s' % (temp_dir))

            # Acquire a lock (file) so acquire inside download will fail
            with open(lock_file.lock_file, 'w') as fp:
                fp.write('')

            expected_msg = 'Timeout waiting to acquire lock for'
            self.assertRaisesRegexp(LockTimeout, expected_msg, action.run, packs=['test'],
                                    abs_repo_base=self.repo_base)
        finally:
            os.unlink(lock_file.lock_file)
            LockFile.acquire = original_acquire

    def test_run_pack_lock_is_already_acquired_force_flag(self):
        # Lock is already acquired but force is true so it should be deleted and released
        action = self.get_action_instance()
        temp_dir = hashlib.md5(PACK_INDEX['test']['repo_url']).hexdigest()

        original_acquire = LockFile.acquire

        def mock_acquire(self, timeout=None):
            original_acquire(self, timeout=0.1)

        LockFile.acquire = mock_acquire

        try:
            lock_file = LockFile('/tmp/%s' % (temp_dir))

            # Acquire a lock (file) so acquire inside download will fail
            with open(lock_file.lock_file, 'w') as fp:
                fp.write('')

            result = action.run(packs=['test'], abs_repo_base=self.repo_base, force=True)
        finally:
            LockFile.acquire = original_acquire

        self.assertEqual(result, {'test': 'Success.'})

    def test_run_pack_download_v_tag(self):
        def side_effect(ref):
            if ref[0] != 'v':
                raise BadName()
            return mock.MagicMock(hexsha='abcdef')

        self.repo_instance.commit.side_effect = side_effect
        self.repo_instance.git = mock.MagicMock(
            branch=(lambda *args: 'master'),
            checkout=(lambda *args: True)
        )

        action = self.get_action_instance()
        result = action.run(packs=['test=1.2.3'], abs_repo_base=self.repo_base)

        self.assertEqual(result, {'test': 'Success.'})

    @mock.patch.object(DownloadGitRepoAction, '_get_valid_versions_for_repo',
                       mock.Mock(return_value=['1.0.0', '2.0.0']))
    def test_run_pack_download_invalid_version(self):
        self.repo_instance.commit.side_effect = lambda ref: None

        action = self.get_action_instance()

        expected_msg = ('is not a valid version, hash, tag or branch.*?'
                        'Available versions are: 1.0.0, 2.0.0.')
        self.assertRaisesRegexp(ValueError, expected_msg, action.run,
                                packs=['test=2.2.3'], abs_repo_base=self.repo_base)

    def test_download_pack_stackstorm_version_identifier_check(self):
        action = self.get_action_instance()

        # Version is satisfied
        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '2.0.0'

        result = action.run(packs=['test3'], abs_repo_base=self.repo_base)
        self.assertEqual(result['test3'], 'Success.')

        # Pack requires a version which is not satisfied by current StackStorm version
        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '2.2.0'
        expected_msg = ('Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
                        'current version is "2.2.0"')
        self.assertRaisesRegexp(ValueError, expected_msg, action.run, packs=['test3'],
                                abs_repo_base=self.repo_base)

        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '2.3.0'
        expected_msg = ('Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
                        'current version is "2.3.0"')
        self.assertRaisesRegexp(ValueError, expected_msg, action.run, packs=['test3'],
                                abs_repo_base=self.repo_base)

        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '1.5.9'
        expected_msg = ('Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
                        'current version is "1.5.9"')
        self.assertRaisesRegexp(ValueError, expected_msg, action.run, packs=['test3'],
                                abs_repo_base=self.repo_base)

        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '1.5.0'
        expected_msg = ('Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
                        'current version is "1.5.0"')
        self.assertRaisesRegexp(ValueError, expected_msg, action.run, packs=['test3'],
                                abs_repo_base=self.repo_base)

        # Version is not met, but force=true parameter is provided
        pack_mgmt.download.CURRENT_STACKSTROM_VERSION = '1.5.0'
        result = action.run(packs=['test3'], abs_repo_base=self.repo_base, force=True)
        self.assertEqual(result['test3'], 'Success.')

    def test_resolve_urls(self):
        url = DownloadGitRepoAction._eval_repo_url(
            "https://github.com/StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = DownloadGitRepoAction._eval_repo_url(
            "https://github.com/StackStorm-Exchange/stackstorm-test.git")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test.git")

        url = DownloadGitRepoAction._eval_repo_url("StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = DownloadGitRepoAction._eval_repo_url("git://StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test")

        url = DownloadGitRepoAction._eval_repo_url("git://StackStorm-Exchange/stackstorm-test.git")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test.git")

        url = DownloadGitRepoAction._eval_repo_url("git@github.com:foo/bar.git")
        self.assertEqual(url, "git@github.com:foo/bar.git")

        url = DownloadGitRepoAction._eval_repo_url("file:///home/vagrant/stackstorm-test")
        self.assertEqual(url, "file:///home/vagrant/stackstorm-test")

        url = DownloadGitRepoAction._eval_repo_url('ssh://<user@host>/AutomationStackStorm')
        self.assertEqual(url, 'ssh://<user@host>/AutomationStackStorm')

        url = DownloadGitRepoAction._eval_repo_url('ssh://joe@local/AutomationStackStorm')
        self.assertEqual(url, 'ssh://joe@local/AutomationStackStorm')

    def test_run_pack_download_edge_cases(self):
        """
        Edge cases to test:

        default branch is master, ref is pack version
        default branch is master, ref is branch name
        default branch is master, ref is default branch name
        default branch is not master, ref is pack version
        default branch is not master, ref is branch name
        default branch is not master, ref is default branch name
        """

        def side_effect(ref):
            if ref[0] != 'v':
                raise BadName()
            return mock.MagicMock(hexsha='abcdeF')

        self.repo_instance.commit.side_effect = side_effect

        edge_cases = {
            'master': '1.2.3',
            'master': 'some-branch',
            'master': 'default-branch',
            'master': None,
            'default-branch': '1.2.3',
            'default-branch': 'some-branch',
            'default-branch': 'default-branch',
            'default-branch': None
        }

        for default_branch, ref in edge_cases.items():
            self.repo_instance.git = mock.MagicMock(
                branch=(lambda *args: default_branch),
                checkout=(lambda *args: True)
            )

            # Set default branch
            self.repo_instance.active_branch.name = default_branch
            self.repo_instance.active_branch.object = 'aBcdef'
            self.repo_instance.head.commit = 'aBcdef'

            # Fake gitref object
            gitref = mock.MagicMock(hexsha='abcDef')

            # Fool _get_gitref into working when its ref == our ref
            def fake_commit(arg_ref):
                if arg_ref == ref:
                    return gitref
                else:
                    raise BadName()
            self.repo_instance.commit = fake_commit
            self.repo_instance.active_branch.object = gitref

            action = self.get_action_instance()

            if ref:
                packs = ['test=%s' % (ref)]
            else:
                packs = ['test']

            result = action.run(packs=packs, abs_repo_base=self.repo_base)
            self.assertEqual(result, {'test': 'Success.'})
