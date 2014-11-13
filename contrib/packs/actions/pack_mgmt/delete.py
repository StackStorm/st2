import os
import pipes
import shutil

from oslo.config import cfg

import st2common.config as config
from st2actions.runners.pythonrunner import Action
from st2common.constants.pack import SYSTEM_PACK_NAME

BLOCKED_PACKS = frozenset([SYSTEM_PACK_NAME])


class UninstallPackAction(Action):
    def __init__(self, config=None):
        super(UninstallPackAction, self).__init__(config=config)
        self.initialize()

        # TODO: Use config base path + virtualenv suffix
        self._base_virtualenvs_path = os.path.join(cfg.CONF.content.packs_base_path,
                                                   'virtualenvs/')

    def initialize(self):
        try:
            config.parse_args()
        except:
            pass

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
            virtualenv_path = os.path.join(self._base_virtualenvs_path, pack_name)

            if os.path.isdir(virtualenv_path):
                self.logger.debug('Deleting virtualenv "%s" for pack "%s"' %
                                  (virtualenv_path, pack_name))
                shutil.rmtree(virtualenv_path)
