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

import six

from st2common.constants.pack import PACK_VERSION_SEPARATOR
from st2common.content.utils import get_pack_base_path
from st2common.runners.base_action import Action
from st2common.util.pack import get_pack_metadata

STACKSTORM_EXCHANGE_PACK = 'StackStorm-Exchange/stackstorm-'
LOCAL_FILE_PREFIX = 'file://'


class GetPackDependencies(Action):
    def __init__(self, config=None, action_service=None):
        self.dependency_list = []
        self.conflict_list = []

    def run(self, packs_status, nested):
        """
        :param packs_status: Name of the pack in Exchange or a git repo URL and download status.
        :type: packs_status: ``dict``

        :param nested: Nested level of dependencies to prevent infinite or really
        long download loops.
        :type nested: ``integer``
        """
        result = {}

        if not packs_status or nested == 0:
            return result

        for pack, status in six.iteritems(packs_status):
            if 'success' not in status.lower():
                continue

            dependency_packs = get_dependency_list(pack)
            if not dependency_packs:
                continue

            for dependency_pack in dependency_packs:
                pack_and_version = dependency_pack.split(PACK_VERSION_SEPARATOR)
                name_or_url = pack_and_version[0]
                pack_version = pack_and_version[1] if len(pack_and_version) > 1 else None

                if name_or_url.startswith(LOCAL_FILE_PREFIX):
                    self.get_local_pack_dependencies(name_or_url, pack_version, dependency_pack)
                elif (len(name_or_url.split('/')) == 1 and STACKSTORM_EXCHANGE_PACK not in
                      name_or_url) or STACKSTORM_EXCHANGE_PACK in name_or_url:
                    self.get_exchange_pack_dependencies(name_or_url, pack_version, dependency_pack)
                else:
                    self.get_none_exchange_pack_dependencies(name_or_url, pack_version,
                                                             dependency_pack)

        result['dependency_list'] = self.dependency_list
        result['conflict_list'] = self.conflict_list
        result['nested'] = nested - 1

        return result

    # For StackStorm Exchange packs. E.g.
    # email
    # https://github.com/StackStorm-Exchange/stackstorm-email
    # https://github.com/StackStorm-Exchange/stackstorm-email.git
    def get_exchange_pack_dependencies(self, name_or_url, pack_version, dependency_pack):
        if len(name_or_url.split('/')) == 1:
            pack_name = name_or_url
        else:
            name_or_git = name_or_url.split(STACKSTORM_EXCHANGE_PACK)[-1]
            pack_name = name_or_git if '.git' not in name_or_git else name_or_git.split('.')[0]

        existing_pack_version = get_pack_version(pack_name)
        self.check_conflict(dependency_pack, pack_version, existing_pack_version)

    # For None StackStorm Exchange packs. E.g.
    # https://github.com/EncoreTechnologies/stackstorm-freeipa.git
    # https://github.com/EncoreTechnologies/stackstorm-freeipa
    # https://github.com/EncoreTechnologies/pack.git
    def get_none_exchange_pack_dependencies(self, name_or_url, pack_version, dependency_pack):
        name_or_git = name_or_url.split('/')[-1]
        name = name_or_git if '.git' not in name_or_git else name_or_git.split('.')[0]
        pack_name = name.split('-')[-1] if "stackstorm-" in name else name

        existing_pack_version = get_pack_version(pack_name)
        self.check_conflict(dependency_pack, pack_version, existing_pack_version)

    # For local file. E.g
    # file:///opt/stackstorm/st2/lib/python3.6/site-packages/st2tests/fixtures/packs/dummy_pack_3
    def get_local_pack_dependencies(self, name_or_url, pack_version, dependency_pack):
        pack_name = name_or_url.split("/")[-1]

        existing_pack_version = get_pack_version(pack_name)
        self.check_conflict(dependency_pack, pack_version, existing_pack_version)

    def check_conflict(self, pack, version, existing_version):
        if existing_version:
            existing_version = 'v' + existing_version
            if version and existing_version != version and pack not in self.conflict_list:
                self.conflict_list.append(pack)
        elif pack not in self.dependency_list:
            self.dependency_list.append(pack)


def get_pack_version(pack=None):
    pack_path = get_pack_base_path(pack)
    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        return pack_metadata.get('version', None)
    except Exception:
        return None


def get_dependency_list(pack=None):
    pack_path = get_pack_base_path(pack)

    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        return pack_metadata.get('dependencies', None)
    except Exception:
        print ('Could not open pack.yaml at location %s' % pack_path)
        return None
