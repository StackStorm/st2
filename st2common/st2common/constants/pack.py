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

__all__ = [
    'PACKS_PACK_NAME',
    'SYSTEM_PACK_NAME',
    'PACKS_PACK_NAME',
    'LINUX_PACK_NAME',
    'SYSTEM_PACK_NAMES',
    'CHATOPS_PACK_NAME',
    'USER_PACK_NAME_BLACKLIST',
    'BASE_PACK_REQUIREMENTS',
    'MANIFEST_FILE_NAME',
    'CONFIG_SCHEMA_FILE_NAME'
]

# A list of allowed characters for the pack name
PACK_NAME_WHITELIST = r'^[A-Za-z0-9_-]+'

# Name used for system pack
SYSTEM_PACK_NAME = 'core'

# Name used for pack management pack
PACKS_PACK_NAME = 'packs'

# Name used for linux pack
LINUX_PACK_NAME = 'linux'

# Name of the default pack
DEFAULT_PACK_NAME = 'default'

# Name of the chatops pack
CHATOPS_PACK_NAME = 'chatops'

# A list of system pack names
SYSTEM_PACK_NAMES = [
    CHATOPS_PACK_NAME,
    SYSTEM_PACK_NAME,
    PACKS_PACK_NAME,
    LINUX_PACK_NAME
]

# A list of pack names which can't be used by user-supplied packs
USER_PACK_NAME_BLACKLIST = [
    SYSTEM_PACK_NAME,
    PACKS_PACK_NAME
]

# Python requirements which are common to all the packs and are installed into the Python pack
# sandbox (virtualenv)
BASE_PACK_REQUIREMENTS = [
    'six>=1.9.0,<2.0'
]

# Name of the pack manifest file
MANIFEST_FILE_NAME = 'pack.yaml'

# File name for the config schema file
CONFIG_SCHEMA_FILE_NAME = 'config.schema.yaml'
