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
import json

from st2actions.runners.pythonrunner import Action
from st2common.content.utils import get_packs_base_paths

GITINFO_FILE = '.gitinfo'


class PackInfo(Action):
    def run(self, pack, pack_dir="/opt/stackstorm/packs"):
        packs_base_paths = get_packs_base_paths()

        pack_git_info_path = None
        for packs_base_path in packs_base_paths:
            git_info_path = os.path.join(packs_base_path, pack, GITINFO_FILE)

            if os.path.isfile(git_info_path):
                pack_git_info_path = git_info_path
                break

        error = ('Pack %s doesn\'t exist or it doesn\'t contain a valid .gitinfo file' % (pack))

        if not pack_git_info_path:
            raise Exception(error)

        try:
            details = self._parse_git_info_file(git_info_path)
        except Exception as e:
            error = ('Pack %s doesn\'t contain a valid .gitinfo file: %s' % (pack, str(e)))
            raise Exception(error)

        return details

    def _parse_git_info_file(self, file_path):
        with open(file_path) as data_file:
            details = json.load(data_file)
            return details

        return details
