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
from __future__ import print_function

import six

from st2common.constants.pack import PACK_VERSION_SEPARATOR
from st2common.content.utils import get_pack_base_path
from st2common.runners.base_action import Action
from st2common.util.pack import get_pack_metadata


class GetPackDependencies(Action):
    def run(self, packs_status, nested):
        """
        :param packs_status: Name of the pack in Exchange or a git repo URL and download status.
        :type: packs_status: ``dict``

        :param nested: Nested level of dependencies to prevent infinite or really
        long download loops.
        :type nested: ``integer``
        """
        result = {}
        dependency_list = []
        conflict_list = []

        if not packs_status or nested == 0:
            return result

        for pack, status in six.iteritems(packs_status):
            if "success" not in status.lower():
                continue

            dependency_packs = get_dependency_list(pack)
            if not dependency_packs:
                continue

            for dep_pack in dependency_packs:
                name_or_url, pack_version = self.get_name_and_version(dep_pack)

                if len(name_or_url.split("/")) == 1:
                    pack_name = name_or_url
                else:
                    name_or_git = name_or_url.split("/")[-1]
                    pack_name = (
                        name_or_git
                        if ".git" not in name_or_git
                        else name_or_git.split(".")[0]
                    )

                # Check existing pack by pack name
                existing_pack_version = get_pack_version(pack_name)

                # Try one more time to get existing pack version by name if 'stackstorm-' is in
                # pack name
                if not existing_pack_version and "stackstorm-" in pack_name.lower():
                    existing_pack_version = get_pack_version(
                        pack_name.split("stackstorm-")[-1]
                    )

                if existing_pack_version:
                    if existing_pack_version and not existing_pack_version.startswith(
                        "v"
                    ):
                        existing_pack_version = "v" + existing_pack_version
                    if pack_version and not pack_version.startswith("v"):
                        pack_version = "v" + pack_version
                    if (
                        pack_version
                        and existing_pack_version != pack_version
                        and dep_pack not in conflict_list
                    ):
                        conflict_list.append(dep_pack)
                else:
                    conflict = self.check_dependency_list_for_conflict(
                        name_or_url, pack_version, dependency_list
                    )
                    if conflict:
                        conflict_list.append(dep_pack)
                    elif dep_pack not in dependency_list:
                        dependency_list.append(dep_pack)

        result["dependency_list"] = dependency_list
        result["conflict_list"] = conflict_list
        result["nested"] = nested - 1

        return result

    def check_dependency_list_for_conflict(self, name, version, dependency_list):
        conflict = False

        for pack in dependency_list:
            name_or_url, pack_version = self.get_name_and_version(pack)
            if name == name_or_url:
                if version != pack_version:
                    conflict = True
                break

        return conflict

    @staticmethod
    def get_name_and_version(pack):
        pack_and_version = pack.split(PACK_VERSION_SEPARATOR)
        name_or_url = pack_and_version[0]
        pack_version = pack_and_version[1] if len(pack_and_version) > 1 else None

        return name_or_url, pack_version


def get_pack_version(pack=None):
    pack_path = get_pack_base_path(pack)
    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        result = pack_metadata.get("version", None)
    except Exception:
        return None

    return result


def get_dependency_list(pack=None):
    pack_path = get_pack_base_path(pack)

    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        result = pack_metadata.get("dependencies", None)
    except Exception:
        print("Could not open pack.yaml at location %s" % pack_path)
        return None

    return result
