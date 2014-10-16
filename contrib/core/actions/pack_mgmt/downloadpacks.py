import os
import shutil
from git.repo import Repo


ALL_PACKS = '*'
PACK_REPO_ROOT = 'packs'
MANIFEST_FILE = 'st2.yaml'


class InstallGitRepoAction(object):

    def run(self, repo_url=None, abs_repo_base=None, packs=None):
        abs_local_path = self._clone_repo(repo_url)
        try:
            # st2-contrib repo has a top-level packs folder that actually contains the
            pack_abs_local_path = os.path.join(abs_local_path, PACK_REPO_ROOT)
            self._move_packs(abs_repo_base, packs, pack_abs_local_path)
        finally:
            self._cleanup_repo(abs_local_path)

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
        for fp in os.listdir(abs_local_path):
            abs_fp = os.path.join(abs_local_path, fp)
            if InstallGitRepoAction._is_desired_pack(abs_fp, fp, packs):
                shutil.move(abs_fp, os.path.join(abs_repo_base, fp))

    @staticmethod
    def _is_desired_pack(abs_fp, pack_name, packs):
        # Must be a dir.
        if not os.path.isdir(abs_fp):
            return False
        # must contain a manifest file. Empty is ok.
        if not os.path.isfile(os.path.join(abs_fp, MANIFEST_FILE)):
            return False
        # Check if it is a desired pack.
        return ALL_PACKS in packs or pack_name in packs

    @staticmethod
    def _cleanup_repo(abs_local_path):
        # basic lock checking etc?
        shutil.rmtree(abs_local_path)
