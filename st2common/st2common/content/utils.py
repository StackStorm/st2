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
import pipes

from oslo.config import cfg
from st2common.constants.action import LIBS_DIR as ACTION_LIBS_DIR

__all__ = [
    'get_packs_base_paths',
    'get_pack_base_path'
]


def get_packs_base_paths():
    """
    Return a list of base paths which are searched for integration packs.

    :rtype: ``list``
    """
    packs_base_paths = cfg.CONF.content.packs_base_paths or ''
    packs_base_paths = packs_base_paths.split(':')
    return packs_base_paths


def get_pack_base_path(pack_name):
    """
    Return full absolute base path to the content pack directory.

    :param pack_name: Content pack name.
    :type pack_name: ``str``

    :rtype: ``str``
    """
    if not pack_name:
        return None

    packs_base_path = get_packs_base_path()
    pack_base_path = os.path.join(packs_base_path, pipes.quote(pack_name))
    pack_base_path = os.path.abspath(pack_base_path)
    return pack_base_path


def get_entry_point_abs_path(pack=None, entry_point=None):
    """
    Return full absolute path of an action entry point in a pack.

    :param pack_name: Content pack name.
    :type pack_name: ``str``
    :param entry_point: Action entry point.
    :type entry_point: ``str``

    :rtype: ``str``
    """
    if entry_point is not None and len(entry_point) > 0:
        if os.path.isabs(entry_point):
            return entry_point
        return os.path.join(get_packs_base_path(),
                            pipes.quote(pack), 'actions', pipes.quote(entry_point))
    else:
        return None


def get_action_libs_abs_path(pack=None, entry_point=None):
    """
    Return full absolute path of libs for an action.

    :param pack_name: Content pack name.
    :type pack_name: ``str``
    :param entry_point: Action entry point.
    :type entry_point: ``str``

    :rtype: ``str``
    """
    entry_point_abs_path = get_entry_point_abs_path(pack=pack, entry_point=entry_point)
    if entry_point_abs_path is not None:
        return os.path.join(os.path.dirname(entry_point_abs_path), ACTION_LIBS_DIR)
    else:
        return None
