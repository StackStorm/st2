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

__all__ = [
    'get_packs_base_path',
    'get_pack_base_path'
]


def get_packs_base_path():
    return cfg.CONF.content.packs_base_path


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
