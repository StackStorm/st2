import os
import shutil
import hashlib
import re
import json

import six
from git.repo import Repo
from lockfile import LockFile

from st2actions.runners.pythonrunner import Action

ALL_PACKS = '*'
PACK_REPO_ROOT = 'packs'
MANIFEST_FILE = 'pack.yaml'
CONFIG_FILE = 'config.yaml'
GITINFO_FILE = '.gitinfo'
PACK_RESERVE_CHARACTER = '.'


class InstallGitRepoAction(Action):
    def run(self, packs, repo_url, abs_repo_base, verifyssl=True, branch='master', subtree=False):
        self._subtree = self._eval_subtree(repo_url, subtree)
        self._repo_url = self._eval_repo_url(repo_url)

        repo_name = self._repo_url[self._repo_url.rfind('/') + 1: self._repo_url.rfind('.')]
        lock_name = hashlib.md5(repo_name).hexdigest() + '.lock'

        with LockFile('/tmp/%s' % (lock_name)):
            abs_local_path = self._clone_repo(repo_url=self._repo_url, verifyssl=verifyssl,
                                              branch=branch)
            try:
                if self._subtree:
                    # st2-contrib repo has a top-level packs folder that actually contains the
                    pack_abs_local_path = os.path.join(abs_local_path, PACK_REPO_ROOT)
                else:
                    pack_abs_local_path = abs_local_path

                self._tag_pack(pack_abs_local_path, packs, self._subtree)
                result = self._move_packs(abs_repo_base, packs, pack_abs_local_path, self._subtree)
            finally:
                self._cleanup_repo(abs_local_path)
        return self._validate_result(result=result, packs=packs, repo_url=repo_url)

    @staticmethod
    def _clone_repo(repo_url, verifyssl=True, branch='master'):
        user_home = os.path.expanduser('~')
        # Assuming git url is of form git@github.com:user/git-repo.git
        repo_name = repo_url[repo_url.rfind('/') + 1: repo_url.rfind('.')]
        abs_local_path = os.path.join(user_home, repo_name)

        # Disable SSL cert checking if explictly asked
        if not verifyssl:
            os.environ['GIT_SSL_NO_VERIFY'] = 'true'

        Repo.clone_from(repo_url, abs_local_path, branch=branch)
        return abs_local_path

    def _move_packs(self, abs_repo_base, packs, abs_local_path, subtree):
        result = {}
        # all_packs should be removed as a pack with that name is not expected to be found.
        if ALL_PACKS in packs:
            packs = os.listdir(abs_local_path)
        for pack in packs:
            abs_pack_temp_location = os.path.join(abs_local_path, pack) if subtree else abs_local_path
            desired, message = InstallGitRepoAction._is_desired_pack(abs_pack_temp_location, pack)
            if desired:
                to = abs_repo_base
                dest_pack_path = os.path.join(abs_repo_base, pack)
                if os.path.exists(dest_pack_path):
                    self.logger.debug('Removing existing pack %s in %s to replace.', pack,
                                      dest_pack_path)
                    # Ensure to preserve any existing configuration
                    old_config_file = os.path.join(dest_pack_path, CONFIG_FILE)
                    new_config_file = os.path.join(abs_pack_temp_location, CONFIG_FILE)
                    shutil.move(old_config_file, new_config_file)
                    shutil.rmtree(dest_pack_path)
                self.logger.debug('Moving pack from %s to %s.', abs_pack_temp_location, to)
                shutil.move(abs_pack_temp_location, to)
                message = 'Success.'
            elif message:
                message = 'Failure : %s' % message
            result[pack] = (desired, message)
        return result

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
        st2_repos = re.compile("st2(contrib|incubator)")
        match = True if st2_repos.search(repo_url) else False
        return subtree ^ match

    @staticmethod
    def _eval_repo_url(repo_url):
        """Allow passing short GitHub style URLs"""
        has_git_extension = repo_url.endswith('.git')
        if len(repo_url.split('/')) == 2 and not "git@" in repo_url:
            url = "https://github.com/{}".format(repo_url)
        else:
            url = repo_url
        return url if has_git_extension else "{}.git".format(url)

    @staticmethod
    def _tag_pack(pack_dir, packs, subtree):
        """Add git information to pack directory for retrieval later"""
        for pack in packs:
            repo = Repo(pack_dir)
            payload = {
                "branch": repo.active_branch.name,
                "ref": repo.head.commit.hexsha
            }

            if subtree:
                info_file = os.path.join(pack_dir, pack, GITINFO_FILE)
            else:
                info_file = os.path.join(pack_dir, GITINFO_FILE)

            try:
                gitinfo = open(info_file, "w")
                gitinfo.write(json.dumps(payload))
            finally:
                gitinfo.close()
