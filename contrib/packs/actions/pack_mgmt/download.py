import os
import shutil
import six
from git.repo import Repo

from st2actions.runners.pythonrunner import Action

ALL_PACKS = '*'
PACK_REPO_ROOT = 'packs'
MANIFEST_FILE = 'pack.yaml'
PACK_RESERVE_CHARACTER = '.'


class InstallGitRepoAction(Action):

    def run(self, packs, repo_url, abs_repo_base):
        abs_local_path = self._clone_repo(repo_url)
        try:
            # st2-contrib repo has a top-level packs folder that actually contains the
            pack_abs_local_path = os.path.join(abs_local_path, PACK_REPO_ROOT)
            result = self._move_packs(abs_repo_base, packs, pack_abs_local_path)
        finally:
            self._cleanup_repo(abs_local_path)
        return self._validate_result(result, packs)

    @staticmethod
    def _clone_repo(repo_url):
        user_home = os.path.expanduser('~')
        # Assuming git url is of form git@github.com:user/git-repo.git
        repo_name = repo_url[repo_url.rfind('/') + 1: repo_url.rfind('.')]
        abs_local_path = os.path.join(user_home, repo_name)
        Repo.clone_from(repo_url, abs_local_path)
        return abs_local_path

    @staticmethod
    def _move_packs(abs_repo_base, packs, abs_local_path):
        result = {}
        # all_packs should be removed as a pack with that name is not expected to be found.
        if ALL_PACKS in packs:
            packs = os.listdir(abs_local_path)
        for pack in packs:
            abs_pack_temp_location = os.path.join(abs_local_path, pack)
            desired, message = InstallGitRepoAction._is_desired_pack(abs_pack_temp_location, pack)
            if desired:
                shutil.move(abs_pack_temp_location, os.path.join(abs_repo_base, pack))
                message = 'Success.'
            elif message:
                message = 'Failure : %s' % message
            result[pack] = (desired, message)
        return result

    @staticmethod
    def _is_desired_pack(abs_pack_path, pack_name):
        # path has to exists.
        if not os.path.exists(abs_pack_path):
            return (False, 'Pack %s not found.' % pack_name)
        # Must be a dir.
        if not os.path.isdir(abs_pack_path):
            return (False, '%s is not a expected directory structure.' % pack_name)
        # should not include reserve characters
        if PACK_RESERVE_CHARACTER in pack_name:
            return (False, 'Pack name "%s" contains reserve character "%s"' %
                    (pack_name, PACK_RESERVE_CHARACTER))
        # must contain a manifest file. Empty file is ok for now.
        if not os.path.isfile(os.path.join(abs_pack_path, MANIFEST_FILE)):
            return (False, 'Pack manifest not found.')
        return (True, '')

    @staticmethod
    def _cleanup_repo(abs_local_path):
        # basic lock checking etc?
        shutil.rmtree(abs_local_path)

    @staticmethod
    def _validate_result(result, packs):
        atleast_one_success = False
        sanitized_result = {}
        for k, v in six.iteritems(result):
            atleast_one_success |= v[0]
            sanitized_result[k] = v[1]
        if not atleast_one_success:
            raise Exception('No packs from %s were downloaded.' % packs)
        return sanitized_result
