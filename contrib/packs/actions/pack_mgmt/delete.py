import os
import pipes
import shutil

from st2actions.runners.pythonrunner import Action

BLOCKED_PACKS = frozenset(['core'])

# TODO: Use config base path + virtualenv suffix
VIRTUALENVS_PATH = '/opt/stackstorm/virtualenvs/'


class UninstallPackAction(Action):

    def run(self, abs_repo_base=None, packs=None):
        intersection = BLOCKED_PACKS & frozenset(packs)
        if len(intersection) > 0:
            raise Exception('Uninstall includes an uninstallable pack - %s.' % list(intersection))

        # 1. Delete pack content
        for fp in os.listdir(abs_repo_base):
            abs_fp = os.path.join(abs_repo_base, fp)
            if fp in packs and os.path.isdir(abs_fp):
                self.logger.debug('Deleting pack directory "%s"' % (abs_fp))
                shutil.rmtree(abs_fp)

        # 2. Delete pack virtual environment
        for pack_name in packs:
            pack_name = pipes.quote(pack_name)
            virtualenv_path = os.path.join(VIRTUALENVS_PATH, pack_name)

            if os.path.isdir(virtualenv_path):
                self.logger.debug('Deleting virtualenv "%s" for pack "%s"' %
                                  (virtualenv_path, pack_name))
                shutil.rmtree(virtualenv_path)


if __name__ == '__main__':
    action = UninstallPackAction()
    action.run('/home/manas/repo_base',
               ['fabric'])
