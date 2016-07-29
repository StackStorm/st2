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

import six
from git.repo import Repo
from lockfile import LockFile

from st2actions.runners.pythonrunner import Action
from st2common.util.green import shell

MANIFEST_FILE = 'pack.yaml'
CONFIG_FILE = 'config.yaml'
GITINFO_FILE = '.gitinfo'
PACK_RESERVE_CHARACTER = '.'

PACK_GROUP_CFG_KEY = 'pack_group'
EXCHANGE_URL_KEY = 'exchange_url'


class DownloadGitRepoAction(Action):
    def __init__(self, config=None, action_service=None):
        super(DownloadGitRepoAction, self).__init__(config=config, action_service=action_service)

    def run(self, pack, version, abs_repo_base, verifyssl=True):

        self._pack_name, self._pack_url = self._get_pack_name_and_url(
            pack,
            self.config.get(EXCHANGE_URL_KEY, None)
        )

        lock_name = hashlib.md5(self._pack_name).hexdigest() + '.lock'

        with LockFile('/tmp/%s' % (lock_name)):
            abs_local_path = self._clone_repo(repo_name=self._pack_name, repo_url=self._pack_url,
                                              verifyssl=verifyssl, branch=version)
            try:
                result = self._move_pack(abs_repo_base, self._pack_name, abs_local_path)
            finally:
                self._cleanup_repo(abs_local_path)

        return self._validate_result(result=result, repo_url=self._pack_url)

    @staticmethod
    def _clone_repo(repo_name, repo_url, verifyssl=True, branch='master'):
        user_home = os.path.expanduser('~')
        abs_local_path = os.path.join(user_home, repo_name)

        # Disable SSL cert checking if explictly asked
        if not verifyssl:
            os.environ['GIT_SSL_NO_VERIFY'] = 'true'
        # Shallow clone the repo to avoid getting all the metadata. We only need HEAD of a
        # specific branch so save some download time.
        Repo.clone_from(repo_url, abs_local_path, branch=branch, depth=1)
        return abs_local_path

    def _move_pack(self, abs_repo_base, pack_name, abs_local_path):
        result = {}

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
            shutil.move(abs_local_path, to)
            # post move fix all permissions.
            self._apply_pack_permissions(pack_path=dest_pack_path)
            message = 'Success.'
        elif message:
            message = 'Failure : %s' % message

        result[pack_name] = (desired, message)

        return result

    def _apply_pack_permissions(self, pack_path):
        """
        Will recursively apply permission 770 to pack and its contents.
        """
        # 1. switch owner group to configured group
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
    def _get_pack_name_and_url(name_or_url, exchange_url):
        if len(name_or_url.split('/')) == 1:
            return (name_or_url, "{}/{}.git".format(exchange_url, name_or_url))
        else:
            return (DownloadGitRepoAction._eval_repo_name(name_or_url),
                    DownloadGitRepoAction._eval_repo_url(name_or_url))

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
