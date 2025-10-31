#!/usr/bin/env python

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

import os
import mock
import shutil
import tempfile
import hashlib
import sys

# TODO: Move keywords directly to hashlib.md5 call as part of dropping py3.8.
hashlib_kwargs = {} if sys.version_info[0:2] < (3, 9) else {"usedforsecurity": False}

from st2common.util.monkey_patch import use_select_poll_workaround

use_select_poll_workaround()

from lockfile import LockFile
from lockfile import LockTimeout
from git.repo import Repo
from gitdb.exc import BadName
from st2common.services import packs as pack_service
from st2tests.base import BaseActionTestCase

import st2common.util.pack_management
from st2common.util.pack_management import eval_repo_url

from pack_mgmt.download import DownloadGitRepoAction

# this import allows pants to detect that the fixtures are used in this file
from .fixtures import FIXTURES_DIR

PACK_INDEX = {
    "test": {
        "version": "0.4.0",
        "name": "test",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test",
        "author": "st2-dev",
        "keywords": ["some", "search", "another", "terms"],
        "email": "info@stackstorm.com",
        "description": "st2 pack to test package management pipeline",
    },
    "test2": {
        "version": "0.5.0",
        "name": "test2",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test2",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
    },
    "test3": {
        "version": "0.5.0",
        "stackstorm_version": ">=1.6.0, <2.2.0",
        "name": "test3",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test3",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
    },
    "test4": {
        "version": "0.5.0",
        "name": "test4",
        "repo_url": "https://github.com/StackStorm-Exchange/stackstorm-test4",
        "author": "stanley",
        "keywords": ["some", "special", "terms"],
        "email": "info@stackstorm.com",
        "description": "another st2 pack to test package management pipeline",
    },
}


original_is_dir_func = os.path.isdir


def mock_is_dir_func(path):
    """
    Mock function which returns True if path ends with .git
    """
    if path.endswith(".git"):
        return True
    return original_is_dir_func(path)


def mock_get_gitref(repo, ref):
    """
    Mock get_gitref function which return mocked object if ref passed is
    PACK_INDEX['test']['version']
    """
    if PACK_INDEX["test"]["version"] in ref:
        if ref[0] == "v":
            return mock.MagicMock(hexsha=PACK_INDEX["test"]["version"])
        else:
            return None
    elif ref:
        return mock.MagicMock(hexsha="abcDef")
    else:
        return None


@mock.patch.object(
    pack_service, "fetch_pack_index", mock.MagicMock(return_value=(PACK_INDEX, {}))
)
class DownloadGitRepoActionTestCase(BaseActionTestCase):
    action_cls = DownloadGitRepoAction

    def setUp(self):
        super(DownloadGitRepoActionTestCase, self).setUp()

        clone_from = mock.patch.object(Repo, "clone_from")

        self.addCleanup(clone_from.stop)
        self.clone_from = clone_from.start()

        self.expand_user_path = tempfile.mkdtemp()
        expand_user = mock.patch.object(
            os.path, "expanduser", mock.MagicMock(return_value=self.expand_user_path)
        )

        self.addCleanup(expand_user.stop)
        self.expand_user = expand_user.start()

        self.repo_base = tempfile.mkdtemp()

        self.repo_instance = mock.MagicMock()
        type(self.repo_instance).active_branch = mock.Mock()

        def side_effect(url, to_path, **kwargs):
            # Since we have no way to pass pack name here, we would have to derive it from repo url
            fixture_name = url.split("/")[-1]
            fixture_path = os.path.join(
                self._get_base_pack_path(), "tests/fixtures", fixture_name
            )
            shutil.copytree(fixture_path, to_path)
            return self.repo_instance

        self.clone_from.side_effect = side_effect

    def tearDown(self):
        shutil.rmtree(self.repo_base)
        shutil.rmtree(self.expand_user())

    def test_run_pack_download(self):
        action = self.get_action_instance()
        result = action.run(packs=["test"], abs_repo_base=self.repo_base)
        temp_dir = hashlib.md5(
            PACK_INDEX["test"]["repo_url"].encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        self.assertEqual(result, {"test": "Success."})
        self.clone_from.assert_called_once_with(
            PACK_INDEX["test"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dir),
        )
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test/pack.yaml")))

        self.repo_instance.git.checkout.assert_called()
        self.repo_instance.git.branch.assert_called()
        self.repo_instance.git.checkout.assert_called()

    def test_run_pack_download_dependencies(self):
        action = self.get_action_instance()
        result = action.run(
            packs=["test"],
            dependency_list=["test2", "test4"],
            abs_repo_base=self.repo_base,
        )
        temp_dirs = [
            hashlib.md5(
                PACK_INDEX["test2"]["repo_url"].encode(), **hashlib_kwargs
            ).hexdigest(),  # nosec. remove nosec after py3.8 drop
            hashlib.md5(
                PACK_INDEX["test4"]["repo_url"].encode(), **hashlib_kwargs
            ).hexdigest(),  # nosec. remove nosec after py3.8 drop
        ]

        self.assertEqual(result, {"test2": "Success.", "test4": "Success."})
        self.clone_from.assert_any_call(
            PACK_INDEX["test2"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dirs[0]),
        )
        self.clone_from.assert_any_call(
            PACK_INDEX["test4"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dirs[1]),
        )
        self.assertEqual(self.clone_from.call_count, 2)
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test2/pack.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test4/pack.yaml")))

    def test_run_pack_download_existing_pack(self):
        action = self.get_action_instance()
        action.run(packs=["test"], abs_repo_base=self.repo_base)
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test/pack.yaml")))

        result = action.run(packs=["test"], abs_repo_base=self.repo_base)

        self.assertEqual(result, {"test": "Success."})

    def test_run_pack_download_multiple_packs(self):
        action = self.get_action_instance()
        result = action.run(packs=["test", "test2"], abs_repo_base=self.repo_base)
        temp_dirs = [
            hashlib.md5(
                PACK_INDEX["test"]["repo_url"].encode(), **hashlib_kwargs
            ).hexdigest(),  # nosec. remove nosec after py3.8 drop
            hashlib.md5(
                PACK_INDEX["test2"]["repo_url"].encode(), **hashlib_kwargs
            ).hexdigest(),  # nosec. remove nosec after py3.8 drop
        ]

        self.assertEqual(result, {"test": "Success.", "test2": "Success."})
        self.clone_from.assert_any_call(
            PACK_INDEX["test"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dirs[0]),
        )
        self.clone_from.assert_any_call(
            PACK_INDEX["test2"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dirs[1]),
        )
        self.assertEqual(self.clone_from.call_count, 2)
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test/pack.yaml")))
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test2/pack.yaml")))

    @mock.patch.object(Repo, "clone_from")
    def test_run_pack_download_error(self, clone_from):
        clone_from.side_effect = Exception(
            "Something went terribly wrong during the clone"
        )

        action = self.get_action_instance()
        self.assertRaises(
            Exception, action.run, packs=["test"], abs_repo_base=self.repo_base
        )

    def test_run_pack_download_no_tag(self):
        self.repo_instance.commit.side_effect = BadName

        action = self.get_action_instance()
        self.assertRaises(
            ValueError, action.run, packs=["test=1.2.3"], abs_repo_base=self.repo_base
        )

    def test_run_pack_lock_is_already_acquired(self):
        action = self.get_action_instance()
        temp_dir = hashlib.md5(
            PACK_INDEX["test"]["repo_url"].encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        original_acquire = LockFile.acquire

        def mock_acquire(self, timeout=None):
            original_acquire(self, timeout=0.1)

        LockFile.acquire = mock_acquire

        try:
            lock_file = LockFile("/tmp/%s" % (temp_dir))

            # Acquire a lock (file) so acquire inside download will fail
            with open(lock_file.lock_file, "w") as fp:
                fp.write("")

            expected_msg = "Timeout waiting to acquire lock for"
            self.assertRaisesRegex(
                LockTimeout,
                expected_msg,
                action.run,
                packs=["test"],
                abs_repo_base=self.repo_base,
            )
        finally:
            os.unlink(lock_file.lock_file)
            LockFile.acquire = original_acquire

    def test_run_pack_lock_is_already_acquired_force_flag(self):
        # Lock is already acquired but force is true so it should be deleted and released
        action = self.get_action_instance()
        temp_dir = hashlib.md5(
            PACK_INDEX["test"]["repo_url"].encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        original_acquire = LockFile.acquire

        def mock_acquire(self, timeout=None):
            original_acquire(self, timeout=0.1)

        LockFile.acquire = mock_acquire

        try:
            lock_file = LockFile("/tmp/%s" % (temp_dir))

            # Acquire a lock (file) so acquire inside download will fail
            with open(lock_file.lock_file, "w") as fp:
                fp.write("")

            result = action.run(
                packs=["test"], abs_repo_base=self.repo_base, force=True
            )
        finally:
            LockFile.acquire = original_acquire

        self.assertEqual(result, {"test": "Success."})

    def test_run_pack_download_v_tag(self):
        def side_effect(ref):
            if ref[0] != "v":
                raise BadName()
            return mock.MagicMock(hexsha="abcdef")

        self.repo_instance.commit.side_effect = side_effect
        self.repo_instance.git = mock.MagicMock(
            branch=(lambda *args: "master"), checkout=(lambda *args: True)
        )

        action = self.get_action_instance()
        result = action.run(packs=["test=1.2.3"], abs_repo_base=self.repo_base)

        self.assertEqual(result, {"test": "Success."})

    @mock.patch.object(
        st2common.util.pack_management,
        "get_valid_versions_for_repo",
        mock.Mock(return_value=["1.0.0", "2.0.0"]),
    )
    def test_run_pack_download_invalid_version(self):
        self.repo_instance.commit.side_effect = lambda ref: None

        action = self.get_action_instance()

        expected_msg = (
            "is not a valid version, hash, tag or branch.*?"
            "Available versions are: 1.0.0, 2.0.0."
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["test=2.2.3"],
            abs_repo_base=self.repo_base,
        )

    def test_download_pack_stackstorm_version_identifier_check(self):
        action = self.get_action_instance()

        # Version is satisfied
        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "2.0.0"

        result = action.run(packs=["test3"], abs_repo_base=self.repo_base)
        self.assertEqual(result["test3"], "Success.")

        # Pack requires a version which is not satisfied by current StackStorm version
        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "2.2.0"
        expected_msg = (
            'Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
            'current version is "2.2.0"'
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["test3"],
            abs_repo_base=self.repo_base,
        )

        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "2.3.0"
        expected_msg = (
            'Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
            'current version is "2.3.0"'
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["test3"],
            abs_repo_base=self.repo_base,
        )

        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "1.5.9"
        expected_msg = (
            'Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
            'current version is "1.5.9"'
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["test3"],
            abs_repo_base=self.repo_base,
        )

        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "1.5.0"
        expected_msg = (
            'Pack "test3" requires StackStorm ">=1.6.0, <2.2.0", but '
            'current version is "1.5.0"'
        )
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["test3"],
            abs_repo_base=self.repo_base,
        )

        # Version is not met, but force=true parameter is provided
        st2common.util.pack_management.CURRENT_STACKSTORM_VERSION = "1.5.0"
        result = action.run(packs=["test3"], abs_repo_base=self.repo_base, force=True)
        self.assertEqual(result["test3"], "Success.")

    def test_download_pack_python_version_check(self):
        action = self.get_action_instance()

        # No python_versions attribute specified in the metadata file
        with mock.patch(
            "st2common.util.pack_management.get_pack_metadata"
        ) as mock_get_pack_metadata:
            mock_get_pack_metadata.return_value = {
                "name": "test3",
                "stackstorm_version": "",
                "python_versions": [],
            }

            st2common.util.pack_management.six.PY2 = True
            st2common.util.pack_management.six.PY3 = False
            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "2.7.11"

            result = action.run(
                packs=["test3"], abs_repo_base=self.repo_base, force=False
            )
            self.assertEqual(result["test3"], "Success.")

        # Pack works with Python 2.x installation is running 2.7
        with mock.patch(
            "st2common.util.pack_management.get_pack_metadata"
        ) as mock_get_pack_metadata:
            mock_get_pack_metadata.return_value = {
                "name": "test3",
                "stackstorm_version": "",
                "python_versions": ["2"],
            }

            st2common.util.pack_management.six.PY2 = True
            st2common.util.pack_management.six.PY3 = False
            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "2.7.5"

            result = action.run(
                packs=["test3"], abs_repo_base=self.repo_base, force=False
            )
            self.assertEqual(result["test3"], "Success.")

            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "2.7.12"

            result = action.run(
                packs=["test3"], abs_repo_base=self.repo_base, force=False
            )
            self.assertEqual(result["test3"], "Success.")

        # Pack works with Python 2.x installation is running 3.5
        with mock.patch(
            "st2common.util.pack_management.get_pack_metadata"
        ) as mock_get_pack_metadata:
            mock_get_pack_metadata.return_value = {
                "name": "test3",
                "stackstorm_version": "",
                "python_versions": ["2"],
            }

            st2common.util.pack_management.six.PY2 = False
            st2common.util.pack_management.six.PY3 = True

            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "3.5.2"

            expected_msg = (
                r'Pack "test3" requires Python 2.x, but current Python version is '
                '"3.5.2"'
            )
            self.assertRaisesRegex(
                ValueError,
                expected_msg,
                action.run,
                packs=["test3"],
                abs_repo_base=self.repo_base,
                force=False,
            )

        # Pack works with Python 3.x installation is running 2.7
        with mock.patch(
            "st2common.util.pack_management.get_pack_metadata"
        ) as mock_get_pack_metadata:
            mock_get_pack_metadata.return_value = {
                "name": "test3",
                "stackstorm_version": "",
                "python_versions": ["3"],
            }

            st2common.util.pack_management.six.PY2 = True
            st2common.util.pack_management.six.PY3 = False
            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "2.7.2"

            expected_msg = (
                r'Pack "test3" requires Python 3.x, but current Python version is '
                '"2.7.2"'
            )
            self.assertRaisesRegex(
                ValueError,
                expected_msg,
                action.run,
                packs=["test3"],
                abs_repo_base=self.repo_base,
                force=False,
            )

        # Pack works with Python 2.x and 3.x installation is running 2.7 and 3.6.1
        with mock.patch(
            "st2common.util.pack_management.get_pack_metadata"
        ) as mock_get_pack_metadata:
            mock_get_pack_metadata.return_value = {
                "name": "test3",
                "stackstorm_version": "",
                "python_versions": ["2", "3"],
            }

            st2common.util.pack_management.six.PY2 = True
            st2common.util.pack_management.six.PY3 = False
            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "2.7.5"

            result = action.run(
                packs=["test3"], abs_repo_base=self.repo_base, force=False
            )
            self.assertEqual(result["test3"], "Success.")

            st2common.util.pack_management.six.PY2 = False
            st2common.util.pack_management.six.PY3 = True
            st2common.util.pack_management.CURRENT_PYTHON_VERSION = "3.6.1"

            result = action.run(
                packs=["test3"], abs_repo_base=self.repo_base, force=False
            )
            self.assertEqual(result["test3"], "Success.")

    def test_resolve_urls(self):
        url = eval_repo_url("https://github.com/StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url(
            "https://github.com/StackStorm-Exchange/stackstorm-test.git"
        )
        self.assertEqual(
            url, "https://github.com/StackStorm-Exchange/stackstorm-test.git"
        )

        url = eval_repo_url("StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "https://github.com/StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url("git://StackStorm-Exchange/stackstorm-test")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test")

        url = eval_repo_url("git://StackStorm-Exchange/stackstorm-test.git")
        self.assertEqual(url, "git://StackStorm-Exchange/stackstorm-test.git")

        url = eval_repo_url("git@github.com:foo/bar.git")
        self.assertEqual(url, "git@github.com:foo/bar.git")

        url = eval_repo_url("file:///home/vagrant/stackstorm-test")
        self.assertEqual(url, "file:///home/vagrant/stackstorm-test")

        url = eval_repo_url("file://localhost/home/vagrant/stackstorm-test")
        self.assertEqual(url, "file://localhost/home/vagrant/stackstorm-test")

        url = eval_repo_url("ssh://<user@host>/AutomationStackStorm")
        self.assertEqual(url, "ssh://<user@host>/AutomationStackStorm")

        url = eval_repo_url("ssh://joe@local/AutomationStackStorm")
        self.assertEqual(url, "ssh://joe@local/AutomationStackStorm")

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
            if ref[0] != "v":
                raise BadName()
            return mock.MagicMock(hexsha="abcdeF")

        self.repo_instance.commit.side_effect = side_effect

        edge_cases = [
            ("master", "1.2.3"),
            ("master", "some-branch"),
            ("master", "default-branch"),
            ("master", None),
            ("default-branch", "1.2.3"),
            ("default-branch", "some-branch"),
            ("default-branch", "default-branch"),
            ("default-branch", None),
        ]

        for default_branch, ref in edge_cases:
            self.repo_instance.git = mock.MagicMock(
                branch=(lambda *args: default_branch), checkout=(lambda *args: True)
            )

            # Set default branch
            self.repo_instance.active_branch.name = default_branch
            self.repo_instance.active_branch.object = "aBcdef"
            self.repo_instance.head.commit = "aBcdef"

            # Fake gitref object
            gitref = mock.MagicMock(hexsha="abcDef")

            # Fool _get_gitref into working when its ref == our ref
            def fake_commit(arg_ref):
                if not ref or arg_ref == ref:
                    return gitref
                else:
                    raise BadName()

            self.repo_instance.commit = fake_commit
            self.repo_instance.active_branch.object = gitref

            action = self.get_action_instance()

            if ref:
                packs = ["test=%s" % (ref)]
            else:
                packs = ["test"]

            result = action.run(packs=packs, abs_repo_base=self.repo_base)
            self.assertEqual(result, {"test": "Success."})

    @mock.patch("os.path.isdir", mock_is_dir_func)
    def test_run_pack_dowload_local_git_repo_detached_head_state(self):
        action = self.get_action_instance()

        type(self.repo_instance).active_branch = mock.PropertyMock(
            side_effect=TypeError("detached head")
        )

        pack_path = os.path.join(FIXTURES_DIR, "stackstorm-test")

        result = action.run(
            packs=["file://%s" % (pack_path)], abs_repo_base=self.repo_base
        )
        self.assertEqual(result, {"test": "Success."})

        # Verify function has bailed out early
        self.repo_instance.git.checkout.assert_not_called()
        self.repo_instance.git.branch.assert_not_called()
        self.repo_instance.git.checkout.assert_not_called()

    def test_run_pack_download_local_directory(self):
        action = self.get_action_instance()

        # 1. Local directory doesn't exist
        expected_msg = r'Local pack directory ".*" doesn\'t exist'
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            action.run,
            packs=["file://doesnt_exist"],
            abs_repo_base=self.repo_base,
        )

        # 2. Local pack which is not a git repository
        pack_path = os.path.join(FIXTURES_DIR, "stackstorm-test4")

        result = action.run(
            packs=["file://%s" % (pack_path)], abs_repo_base=self.repo_base
        )
        self.assertEqual(result, {"test4": "Success."})

        # Verify pack contents have been copied over
        destination_path = os.path.join(self.repo_base, "test4")
        self.assertTrue(os.path.exists(destination_path))
        self.assertTrue(os.path.exists(os.path.join(destination_path, "pack.yaml")))

    @mock.patch("st2common.util.pack_management.get_gitref", mock_get_gitref)
    def test_run_pack_download_with_tag(self):
        action = self.get_action_instance()
        result = action.run(packs=["test"], abs_repo_base=self.repo_base)
        temp_dir = hashlib.md5(
            PACK_INDEX["test"]["repo_url"].encode(), **hashlib_kwargs
        ).hexdigest()  # nosec. remove nosec after py3.8 drop

        self.assertEqual(result, {"test": "Success."})
        self.clone_from.assert_called_once_with(
            PACK_INDEX["test"]["repo_url"],
            os.path.join(os.path.expanduser("~"), ".st2packs", temp_dir),
        )
        self.assertTrue(os.path.isfile(os.path.join(self.repo_base, "test/pack.yaml")))

        # Check repo.git.checkout is called three times
        self.assertEqual(self.repo_instance.git.checkout.call_count, 3)

        # Check repo.git.checkout called with latest tag or branch
        self.assertEqual(
            PACK_INDEX["test"]["version"],
            self.repo_instance.git.checkout.call_args_list[1][0][0],
        )

        # Check repo.git.checkout called with head
        self.assertEqual(
            self.repo_instance.head.reference,
            self.repo_instance.git.checkout.call_args_list[2][0][0],
        )

        self.repo_instance.git.branch.assert_called_with(
            "-f", self.repo_instance.head.reference, PACK_INDEX["test"]["version"]
        )
