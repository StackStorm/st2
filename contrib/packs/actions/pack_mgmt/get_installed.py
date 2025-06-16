# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import yaml

import six

from git.repo import Repo
from git.exc import InvalidGitRepositoryError

from st2common.runners.base_action import Action
from st2common.content.utils import get_packs_base_paths
from st2common.constants.pack import MANIFEST_FILE_NAME


class GetInstalled(Action):
    """Get information about installed pack."""

    def run(self, pack, branch):
        """
        :param pack: Installed Pack Name to get info about
        :type pack: ``str``
        :type branch: ``str``
        """
        packs_base_paths = get_packs_base_paths()

        pack_path = None
        metadata_file = None
        for packs_base_path in packs_base_paths:
            pack_path = os.path.join(packs_base_path, pack)
            pack_yaml_path = os.path.join(pack_path, MANIFEST_FILE_NAME)

            if os.path.isfile(pack_yaml_path):
                metadata_file = pack_yaml_path
                break

        # Pack doesn't exist, finish execution normally with empty metadata
        if not os.path.isdir(pack_path):
            return {"pack": None, "git_status": None}

        if not metadata_file:
            error = 'Pack "%s" doesn\'t contain pack.yaml file.' % (pack)
            raise Exception(error)

        try:
            details = self._parse_yaml_file(metadata_file)
        except Exception as e:
            error = 'Pack "%s" doesn\'t contain a valid pack.yaml file: %s' % (
                pack,
                six.text_type(e),
            )
            raise Exception(error)

        try:
            repo = Repo(pack_path)
            git_status = "Status:\n%s\n\nRemotes:\n%s" % (
                repo.git.status().split("\n")[0],
                "\n".join([remote.url for remote in repo.remotes]),
            )
            ahead_behind = repo.git.rev_list(
                "--left-right", "--count", f"HEAD...origin/{branch}"
            ).split()
            # Dear god.
            if ahead_behind != ["0", "0"]:
                git_status += "\n\n"
                git_status += "%s commits ahead " if ahead_behind[0] != "0" else ""
                git_status += "and " if "0" not in ahead_behind else ""
                git_status += "%s commits behind " if ahead_behind[1] != "0" else ""
                git_status += "origin/master."
        except InvalidGitRepositoryError:
            git_status = None

        return {"pack": details, "git_status": git_status}

    def _parse_yaml_file(self, file_path):
        with open(file_path) as data_file:
            details = yaml.safe_load(data_file)
        return details
