import os
import shutil
from git.repo import Repo


class InstallGitRepoAction(object):

    def run(self, repo_url=None, abs_repo_base=None, packs=None):
        abs_local_path = self._clone_repo(repo_url)
        try:
            self._move_packs(abs_repo_base, packs, abs_local_path)
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
            if fp in packs and os.path.isdir(abs_fp):
                shutil.move(abs_fp, os.path.join(abs_repo_base, fp))

    @staticmethod
    def _cleanup_repo(abs_local_path):
        # basic lock checking etc?
        shutil.rmtree(abs_local_path)


if __name__ == '__main__':
    action = InstallGitRepoAction()
    action.run('git@github.com:StackStorm/st2-contrib.git',
               '/home/manas/repo_base',
               ['fabric'])
