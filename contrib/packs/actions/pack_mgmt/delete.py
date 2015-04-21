import os
import shutil

from oslo.config import cfg

from st2actions.runners.pythonrunner import Action
from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.util.shell import quote_unix

BLOCKED_PACKS = frozenset(SYSTEM_PACK_NAMES)


class UninstallPackAction(Action):
    def __init__(self, config=None):
        super(UninstallPackAction, self).__init__(config=config)
        self._base_virtualenvs_path = os.path.join(cfg.CONF.system.base_path,
                                                   'virtualenvs/')

    def run(self, packs, abs_repo_base):
        intersection = BLOCKED_PACKS & frozenset(packs)
        if len(intersection) > 0:
            names = ', '.join(list(intersection))
            raise ValueError('Uninstall includes an uninstallable pack - %s.' % (names))

        # 1. Delete pack content
        for fp in os.listdir(abs_repo_base):
            abs_fp = os.path.join(abs_repo_base, fp)
            if fp in packs and os.path.isdir(abs_fp):
                self.logger.debug('Deleting pack directory "%s"' % (abs_fp))
                shutil.rmtree(abs_fp)

        # 2. Delete pack virtual environment
        for pack_name in packs:
            pack_name = quote_unix(pack_name)
            virtualenv_path = os.path.join(self._base_virtualenvs_path, pack_name)

            if os.path.isdir(virtualenv_path):
                self.logger.debug('Deleting virtualenv "%s" for pack "%s"' %
                                  (virtualenv_path, pack_name))
                shutil.rmtree(virtualenv_path)
