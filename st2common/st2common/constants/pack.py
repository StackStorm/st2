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

__all__ = [
    "COMMON_LIB_DIR",
    "PACKS_PACK_NAME",
    "PACK_REF_WHITELIST_REGEX",
    "RESERVED_PACK_LIST",
    "PACK_RESERVED_CHARACTERS",
    "PACK_VERSION_SEPARATOR",
    "PACK_VERSION_REGEX",
    "ST2_VERSION_REGEX",
    "SYSTEM_PACK_NAME",
    "PACKS_PACK_NAME",
    "LINUX_PACK_NAME",
    "SYSTEM_PACK_NAMES",
    "CHATOPS_PACK_NAME",
    "USER_PACK_NAME_BLACKLIST",
    "BASE_PACK_REQUIREMENTS",
    "MANIFEST_FILE_NAME",
    "CONFIG_SCHEMA_FILE_NAME",
]

COMMON_LIB_DIR = "lib"

# Prefix for render context w/ config
PACK_CONFIG_CONTEXT_KV_PREFIX = "config_context"

# A list of allowed characters for the pack name
PACK_REF_WHITELIST_REGEX = r"^[a-z0-9_]+$"

# A list of reserved pack names that cannot be used
RESERVED_PACK_LIST = ["_global"]

# Check for a valid semver string
PACK_VERSION_REGEX = r"^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:-[\da-z\-]+(?:\.[\da-z\-]+)*)?(?:\+[\da-z\-]+(?:\.[\da-z\-]+)*)?$"  # noqa

# Special characters which can't be used in pack names
PACK_RESERVED_CHARACTERS = ["."]

# Version sperator when version is supplied in pack name
# Example: libcloud@1.0.1
PACK_VERSION_SEPARATOR = "="

# Check for st2 version in engines
ST2_VERSION_REGEX = r"^((>?>|>=|=|<=|<?<)\s*[0-9]+\.[0-9]+\.[0-9]+?(\s*,)?\s*)+$"

# Name used for system pack
SYSTEM_PACK_NAME = "core"

# Name used for pack management pack
PACKS_PACK_NAME = "packs"

# Name used for linux pack
LINUX_PACK_NAME = "linux"

# Name of the default pack
DEFAULT_PACK_NAME = "default"

# Name of the chatops pack
CHATOPS_PACK_NAME = "chatops"

# A list of system pack names
SYSTEM_PACK_NAMES = [
    CHATOPS_PACK_NAME,
    SYSTEM_PACK_NAME,
    PACKS_PACK_NAME,
    LINUX_PACK_NAME,
]

# A list of pack names which can't be used by user-supplied packs
USER_PACK_NAME_BLACKLIST = [SYSTEM_PACK_NAME, PACKS_PACK_NAME]

# Python requirements which are common to all the packs and are installed into the Python pack
# sandbox (virtualenv)
BASE_PACK_REQUIREMENTS = ["six>=1.9.0,<2.0"]

# Name of the pack manifest file
MANIFEST_FILE_NAME = "pack.yaml"

# File name for the config schema file
CONFIG_SCHEMA_FILE_NAME = "config.schema.yaml"
