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
    "ALLOWED_SCOPES",
    "SYSTEM_SCOPE",
    "FULL_SYSTEM_SCOPE",
    "SYSTEM_SCOPES",
    "USER_SCOPE",
    "FULL_USER_SCOPE",
    "USER_SCOPES",
    "USER_SEPARATOR",
    "DATASTORE_SCOPE_SEPARATOR",
    "DATASTORE_KEY_SEPARATOR",
]

ALL_SCOPE = "all"

# Parent namespace for all items in key-value store
DATASTORE_PARENT_SCOPE = "st2kv"
DATASTORE_SCOPE_SEPARATOR = (
    "."  # To separate scope from datastore namespace. E.g. st2kv.system
)

# Namespace to contain all system/global scoped variables in key-value store.
SYSTEM_SCOPE = "system"
FULL_SYSTEM_SCOPE = "%s%s%s" % (
    DATASTORE_PARENT_SCOPE,
    DATASTORE_SCOPE_SEPARATOR,
    SYSTEM_SCOPE,
)

SYSTEM_SCOPES = [SYSTEM_SCOPE]

# Namespace to contain all user scoped variables in key-value store.
USER_SCOPE = "user"
FULL_USER_SCOPE = "%s%s%s" % (
    DATASTORE_PARENT_SCOPE,
    DATASTORE_SCOPE_SEPARATOR,
    USER_SCOPE,
)

USER_SCOPES = [USER_SCOPE]

USER_SEPARATOR = ":"

# Separator for keys in the datastore
DATASTORE_KEY_SEPARATOR = ":"

ALLOWED_SCOPES = [SYSTEM_SCOPE, USER_SCOPE, FULL_SYSTEM_SCOPE, FULL_USER_SCOPE]
