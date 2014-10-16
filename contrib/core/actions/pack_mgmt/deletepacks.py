import os
import shutil


BLOCKED_PACKS = frozenset(['core'])


class UninstallPackAction(object):

    def run(self, abs_repo_base=None, packs=None):
        intersection = BLOCKED_PACKS & frozenset(packs)
        if len(intersection) > 0:
            raise Exception('Uninstall includes an uninstallable pack - %s.' % list(intersection))
        for fp in os.listdir(abs_repo_base):
            abs_fp = os.path.join(abs_repo_base, fp)
            if fp in packs and os.path.isdir(abs_fp):
                shutil.rmtree(abs_fp)


if __name__ == '__main__':
    action = UninstallPackAction()
    action.run('/home/manas/repo_base',
               ['fabric'])
