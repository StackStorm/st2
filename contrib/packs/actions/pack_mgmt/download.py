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
import json
import stat

import six
from git.repo import Repo
from lockfile import LockFile

from st2actions.runners.pythonrunner import Action
from st2common.util.green import shell

ALL_PACKS = '*'
PACK_REPO_ROOT = 'packs'
MANIFEST_FILE = 'pack.yaml'
CONFIG_FILE = 'config.yaml'
GITINFO_FILE = '.gitinfo'
PACK_RESERVE_CHARACTER = '.'

STACKSTORM_CONTRIB_REPOS = [
    'st2contrib',
    'st2incubator'
]

#####
# !!!!!!!!!!!!!!
# !!! README !!!
# !!!!!!!!!!!!!!
#
# This NEEDS a rewrite. Too many features and far too many assumption
# to keep this impl straight any longer. If you only want to read code do
# so at your own peril.
#
# If you are here to fix a bug or add a feature answer these questions -
# 1. Am I fixing a broken feature?
# 2. Is this the only module in which to fix the bug?
# 3. Am I sure this is a bug fix and not a feature?
#
# Only if you can emphatically answer 'YES' to allow about questions you should
# touch this file. Else, be warned you might loose a part of you soul or sanity.
#####


PACK_GROUP_CFG_KEY = 'pack_group'


class DownloadGitRepoAction(Action):
    def __init__(self, config=None, action_service=None):
        super(DownloadGitRepoAction, self).__init__(config=config, action_service=action_service)
        self._subtree = None
        self._repo_url = None

    def run(self, packs, repo_url, abs_repo_base, verifyssl=True, branch='master', subtree=False):

        cached_repo_url, cached_branch, cached_subtree = self._lookup_cached_gitinfo(
            abs_repo_base, packs)

        if not repo_url:
            repo_url = cached_repo_url
        if not branch:
            branch = cached_branch
        # Making the assumption that is no repo_url change was required
        # the subtree nature should be inferred from cached value.
        if repo_url == cached_repo_url:
            subtree = cached_subtree

        self._subtree = self._eval_subtree(repo_url, subtree)
        self._repo_url = self._eval_repo_url(repo_url)

        repo_name = self._eval_repo_name(self._repo_url)
        lock_name = hashlib.md5(repo_name).hexdigest() + '.lock'

        with LockFile('/tmp/%s' % (lock_name)):
            abs_local_path = self._clone_repo(repo_url=self._repo_url, verifyssl=verifyssl,
                                              branch=branch)
            try:
                if self._subtree:
                    # st2-contrib repo has a top-level packs folder that actually contains the
                    pack_abs_local_path = os.path.join(abs_local_path, PACK_REPO_ROOT)
                    # resolve ALL_PACK here to avoid wild-cards
                    if ALL_PACKS in packs:
                        packs = os.listdir(pack_abs_local_path)
                else:
                    pack_abs_local_path = abs_local_path

                self._tag_pack(pack_abs_local_path, packs, self._subtree)
                result = self._move_packs(abs_repo_base, packs, pack_abs_local_path, self._subtree)
            finally:
                self._cleanup_repo(abs_local_path)
        return self._validate_result(result=result, packs=packs, repo_url=self._repo_url)

    @staticmethod
    def _clone_repo(repo_url, verifyssl=True, branch='master'):
        user_home = os.path.expanduser('~')
        # Assuming git url is of form git@github.com:user/git-repo.git
        repo_name = DownloadGitRepoAction._eval_repo_name(repo_url)
        abs_local_path = os.path.join(user_home, repo_name)

        # Disable SSL cert checking if explictly asked
        if not verifyssl:
            os.environ['GIT_SSL_NO_VERIFY'] = 'true'
        # Shallow clone the repo to avoid getting all the metadata. We only need HEAD of a
        # specific branch so save some download time.
        Repo.clone_from(repo_url, abs_local_path, branch=branch, depth=1)
        return abs_local_path

    def _move_packs(self, abs_repo_base, packs, abs_local_path, subtree):
        result = {}

        for pack in packs:
            if subtree:
                abs_pack_temp_location = os.path.join(abs_local_path, pack)
            else:
                abs_pack_temp_location = abs_local_path

            desired, message = DownloadGitRepoAction._is_desired_pack(abs_pack_temp_location, pack)
            if desired:
                to = abs_repo_base
                dest_pack_path = os.path.join(abs_repo_base, pack)
                if os.path.exists(dest_pack_path):
                    self.logger.debug('Removing existing pack %s in %s to replace.', pack,
                                      dest_pack_path)

                    # Ensure to preserve any existing configuration
                    old_config_file = os.path.join(dest_pack_path, CONFIG_FILE)
                    new_config_file = os.path.join(abs_pack_temp_location, CONFIG_FILE)

                    if os.path.isfile(old_config_file):
                        shutil.move(old_config_file, new_config_file)

                    shutil.rmtree(dest_pack_path)

                self.logger.debug('Moving pack from %s to %s.', abs_pack_temp_location, to)
                shutil.move(abs_pack_temp_location, to)
                # post move fix all permissions.
                self._apply_pack_permissions(pack_path=dest_pack_path)
                message = 'Success.'
            elif message:
                message = 'Failure : %s' % message
            result[pack] = (desired, message)
        return result

    def _apply_pack_permissions(self, pack_path):
        """
        Will recursively apply permission 770 to pack and its contents.
        """
        # 1. switch owner group to configuered group
        pack_group = self.config.get(PACK_GROUP_CFG_KEY, None)
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
        # path has to exists.
        if not os.path.exists(abs_pack_path):
            return (False, 'Pack "%s" not found or it\'s missing a "pack.yaml" file.' %
                    (pack_name))
        # Must be a dir.
        if not os.path.isdir(abs_pack_path):
            return (False, '%s is not a expected directory structure.' % (pack_name))
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
    def _validate_result(result, packs, repo_url):
        atleast_one_success = False
        sanitized_result = {}
        for k, v in six.iteritems(result):
            atleast_one_success |= v[0]
            sanitized_result[k] = v[1]

        if not atleast_one_success:
            message_list = []
            message_list.append('No packs were downloaded from repository "%s".\n' % (repo_url))
            message_list.append('Errors:')

            for pack, value in result.items():
                success, error = value

                if success:
                    continue

                message_list.append(' - %s: %s' % (pack, error))

            message = '\n'.join(message_list)
            raise Exception(message)

        return sanitized_result

    @staticmethod
    def _eval_subtree(repo_url, subtree):
        match = False
        for stackstorm_repo_name in STACKSTORM_CONTRIB_REPOS:
            if stackstorm_repo_name in repo_url:
                match = True
                break

        return subtree | match

    @staticmethod
    def _eval_repo_url(repo_url):
        """Allow passing short GitHub style URLs"""
        if not repo_url:
            raise Exception('No valid reo_url provided or could be inferred.')
        has_git_extension = repo_url.endswith('.git')
        if len(repo_url.split('/')) == 2 and "git@" not in repo_url:
            url = "https://github.com/{}".format(repo_url)
        else:
            url = repo_url
        return url if has_git_extension else "{}.git".format(url)

    @staticmethod
    def _lookup_cached_gitinfo(abs_repo_base, packs):
        """
        This method will try to lookup the repo_url from the first pack in the list
        of packs. It works under some strict assumptions -
        1. repo_url was not originally specified
        2. all packs from from same repo
        3. gitinfo was originally added by this action
        """
        repo_url = None
        branch = None
        subtree = False
        if len(packs) < 1:
            raise Exception('No packs specified.')
        gitinfo_location = os.path.join(abs_repo_base, packs[0], GITINFO_FILE)
        if not os.path.exists(gitinfo_location):
            return repo_url, branch, subtree
        with open(gitinfo_location, 'r') as gitinfo_fp:
            gitinfo = json.load(gitinfo_fp)
            repo_url = gitinfo.get('repo_url', None)
            branch = gitinfo.get('branch', None)
            subtree = gitinfo.get('subtree', False)
        return repo_url, branch, subtree

    @staticmethod
    def _eval_repo_name(repo_url):
        """
        Evaluate the name of the repo.
        https://github.com/StackStorm/st2contrib.git -> st2contrib
        https://github.com/StackStorm/st2contrib -> st2contrib
        git@github.com:StackStorm/st2contrib.git -> st2contrib
        git@github.com:StackStorm/st2contrib -> st2contrib
        """
        last_forward_slash = repo_url.rfind('/')
        next_dot = repo_url.find('.', last_forward_slash)
        # If dot does not follow last_forward_slash return till the end
        if next_dot < last_forward_slash:
            return repo_url[last_forward_slash + 1:]
        return repo_url[last_forward_slash + 1:next_dot]

    def _tag_pack(self, pack_root, packs, subtree):
        """Add git information to pack directory for retrieval later"""

        repo = Repo(pack_root)
        payload = {
            'repo_url': repo.remotes[0].url,
            'branch': repo.active_branch.name,
            'ref': repo.head.commit.hexsha,
            'subtree': subtree
        }

        for pack in packs:
            pack_dir = os.path.join(pack_root, pack) if subtree else pack_root

            if not os.path.exists(pack_dir):
                self.logger.warn('%s is missing. Expected location "%s".', pack, pack_dir)
                continue

            info_file = os.path.join(pack_dir, GITINFO_FILE)

            with open(info_file, "w") as gitinfo:
                gitinfo.write(json.dumps(payload))
