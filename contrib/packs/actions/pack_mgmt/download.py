# -*- coding: utf-8 -*-
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
import shutil
import hashlib
import stat
import re

import six
import yaml
from git.repo import Repo
from gitdb.exc import BadName, BadObject
from lockfile import LockFile

from st2common.runners.base_action import Action
from st2common.content import utils
from st2common.services.packs import get_pack_from_index
from st2common.util.green import shell

MANIFEST_FILE = 'pack.yaml'
CONFIG_FILE = 'config.yaml'
GITINFO_FILE = '.gitinfo'
PACK_RESERVE_CHARACTER = '.'
PACK_VERSION_SEPARATOR = '='
SEMVER_REGEX = (r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
                r"(?:-[\da-z\-]+(?:\.[\da-z\-]+)*)?(?:\+[\da-z\-]+(?:\.[\da-z\-]+)*)?$")


class DownloadGitRepoAction(Action):
    def __init__(self, config=None, action_service=None):
        super(DownloadGitRepoAction, self).__init__(config=config, action_service=action_service)

    def run(self, packs, abs_repo_base, verifyssl=True):
        result = {}

        for pack in packs:
            pack_url, pack_version = self._get_repo_url(pack)
            temp_dir = hashlib.md5(pack_url).hexdigest()

            with LockFile('/tmp/%s' % (temp_dir)):
                try:
                    user_home = os.path.expanduser('~')
                    abs_local_path = os.path.join(user_home, temp_dir)
                    self._clone_repo(temp_dir=abs_local_path, repo_url=pack_url,
                                     verifyssl=verifyssl, ref=pack_version)
                    pack_name = self._get_pack_name(abs_local_path)
                    result[pack_name] = self._move_pack(abs_repo_base, pack_name, abs_local_path)
                finally:
                    self._cleanup_repo(abs_local_path)

        return self._validate_result(result=result, repo_url=pack_url)

    @staticmethod
    def _clone_repo(temp_dir, repo_url, verifyssl=True, ref='master'):
        # Switch to non-interactive mode
        os.environ['GIT_TERMINAL_PROMPT'] = '0'

        # Disable SSL cert checking if explictly asked
        if not verifyssl:
            os.environ['GIT_SSL_NO_VERIFY'] = 'true'

        # Clone the repo from git; we don't use shallow copying
        # because we want the user to work with the repo in the
        # future.
        repo = Repo.clone_from(repo_url, temp_dir)

        # Try to match the reference to a commit hash, a tag, or "master"
        gitref = DownloadGitRepoAction._get_gitref(repo, ref)

        # Try to match the reference to a "vX.Y.Z" tag
        if not gitref and re.match(SEMVER_REGEX, ref):
            gitref = DownloadGitRepoAction._get_gitref(repo, "v%s" % ref)

        # Try to match the reference to a branch name
        if not gitref:
            gitref = DownloadGitRepoAction._get_gitref(repo, "origin/%s" % ref)

        # Giving up ¯\_(ツ)_/¯
        if not gitref:
            raise ValueError(
                "\"%s\" is not a valid version, hash, tag, or branch in %s." % (ref, repo_url)
            )

        # We're trying to figure out which branch the ref is actually on,
        # since there's no direct way to check for this in git-python.
        branches = repo.git.branch('--color=never', '--all', '--contains', gitref.hexsha)
        branches = branches.replace('*', '').split()
        if 'master' not in branches:
            branch = branches[0]
            repo.git.checkout('--track', branches[0])
            branch = repo.head.reference
        else:
            branch = 'master'

        repo.git.checkout('-B', branch, gitref.hexsha)

        return temp_dir

    def _move_pack(self, abs_repo_base, pack_name, abs_local_path):
        desired, message = DownloadGitRepoAction._is_desired_pack(abs_local_path, pack_name)
        if desired:
            to = abs_repo_base
            dest_pack_path = os.path.join(abs_repo_base, pack_name)
            if os.path.exists(dest_pack_path):
                self.logger.debug('Removing existing pack %s in %s to replace.', pack_name,
                                  dest_pack_path)

                # Ensure to preserve any existing configuration
                old_config_file = os.path.join(dest_pack_path, CONFIG_FILE)
                new_config_file = os.path.join(abs_local_path, CONFIG_FILE)

                if os.path.isfile(old_config_file):
                    shutil.move(old_config_file, new_config_file)

                shutil.rmtree(dest_pack_path)

            self.logger.debug('Moving pack from %s to %s.', abs_local_path, to)
            shutil.move(abs_local_path, dest_pack_path)
            # post move fix all permissions.
            self._apply_pack_permissions(pack_path=dest_pack_path)
            message = 'Success.'
        elif message:
            message = 'Failure : %s' % message

        return (desired, message)

    def _apply_pack_permissions(self, pack_path):
        """
        Will recursively apply permission 770 to pack and its contents.
        """
        # 1. switch owner group to configured group
        pack_group = utils.get_pack_group()
        if pack_group:
            shell.run_command(['sudo', 'chgrp', '-R', pack_group, pack_path])

        # 2. Setup the right permissions and group ownership
        # These mask is same as mode = 775
        mode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH
        os.chmod(pack_path, mode)

        # Yuck! Since os.chmod does not support chmod -R walk manually.
        for root, dirs, files in os.walk(pack_path):
            for d in dirs:
                os.chmod(os.path.join(root, d), mode)
            for f in files:
                os.chmod(os.path.join(root, f), mode)

    @staticmethod
    def _is_desired_pack(abs_pack_path, pack_name):
        # path has to exist.
        if not os.path.exists(abs_pack_path):
            return (False, 'Pack "%s" not found or it\'s missing a "pack.yaml" file.' %
                    (pack_name))
        # should not include reserve characters
        if PACK_RESERVE_CHARACTER in pack_name:
            return (False, 'Pack name "%s" contains reserve character "%s"' %
                    (pack_name, PACK_RESERVE_CHARACTER))
        # must contain a manifest file. Empty file is ok for now.
        if not os.path.isfile(os.path.join(abs_pack_path, MANIFEST_FILE)):
            return (False, 'Pack is missing a manifest file (%s).' % (MANIFEST_FILE))
        return (True, '')

    @staticmethod
    def _cleanup_repo(abs_local_path):
        # basic lock checking etc?
        if os.path.isdir(abs_local_path):
            shutil.rmtree(abs_local_path)

    @staticmethod
    def _validate_result(result, repo_url):
        atleast_one_success = False
        sanitized_result = {}
        for k, v in six.iteritems(result):
            atleast_one_success |= v[0]
            sanitized_result[k] = v[1]

        if not atleast_one_success:
            message_list = []
            message_list.append('The pack has not been downloaded from "%s".\n' % (repo_url))
            message_list.append('Errors:')

            for pack, value in result.items():
                success, error = value
                message_list.append(error)

            message = '\n'.join(message_list)
            raise Exception(message)

        return sanitized_result

    @staticmethod
    def _get_repo_url(pack):
        pack_and_version = pack.split(PACK_VERSION_SEPARATOR)
        name_or_url = pack_and_version[0]
        version = pack_and_version[1] if len(pack_and_version) > 1 else None

        if len(name_or_url.split('/')) == 1:
            pack = get_pack_from_index(name_or_url)
            if not pack:
                raise Exception('No record of the "%s" pack in the index.' % name_or_url)
            return (pack['repo_url'], version)
        else:
            return (DownloadGitRepoAction._eval_repo_url(name_or_url), version)

    @staticmethod
    def _eval_repo_url(repo_url):
        """Allow passing short GitHub style URLs"""
        if not repo_url:
            raise Exception('No valid repo_url provided or could be inferred.')
        has_git_extension = repo_url.endswith('.git')
        if len(repo_url.split('/')) == 2 and "git@" not in repo_url:
            url = "https://github.com/{}".format(repo_url)
        else:
            url = repo_url
        return url if has_git_extension else "{}.git".format(url)

    @staticmethod
    def _get_pack_name(pack_dir):
        """
        Read pack name from the metadata file and sanitize it.
        """
        with open(os.path.join(pack_dir, MANIFEST_FILE), 'r') as manifest_file:
            pack_meta = yaml.load(manifest_file)
        return pack_meta['name'].replace(' ', '-').lower()

    @staticmethod
    def _get_gitref(repo, ref):
        try:
            return repo.commit(ref)
        except (BadName, BadObject):
            return False
