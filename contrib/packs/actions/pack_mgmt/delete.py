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

from oslo_config import cfg

from st2actions.runners.pythonrunner import Action
from st2common.constants.pack import SYSTEM_PACK_NAMES
from st2common.util.shell import quote_unix

BLOCKED_PACKS = frozenset(SYSTEM_PACK_NAMES)


class UninstallPackAction(Action):
    def __init__(self, config=None, action_service=None):
        super(UninstallPackAction, self).__init__(config=config, action_service=action_service)
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
