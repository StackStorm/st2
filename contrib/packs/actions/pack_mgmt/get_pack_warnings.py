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


class GetPackWarnings(Action):
    def run(self, packs_status):
        """
        :param packs_status: Name of the pack in Exchange or a git repo URL and download status.
        :type: packs_status: ``dict``
        """
        result = {}
        warning_list = []

        if not packs_status:
            return result

        for pack, status in six.iteritems(packs_status):
            if 'success' not in status.lower():
                continue

            warning = get_warnings(pack)

            if warning:
                warning_list.append(warning)

        result['warning_list'] = warning_list

        return result


def get_warnings(pack=None):
    result = None
    pack_path = get_pack_base_path(pack)
    try:
        pack_metadata = get_pack_metadata(pack_dir=pack_path)
        pack_name = pack_metadata.get('name', None)
        versions = pack_metadata.get('python_versions', None)
        if set(versions) == set(['2']):
            result = "DEPRECATION WARNING: Pack %s only supports Python 2.x. " \
                     "ST2 will remove support for Python 2.x in a future release." \
                     % pack_name
    except Exception:
        print('Could not open pack.yaml at location %s' % pack_path)
    finally:
        return result
