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
    'ALLOWED_SCOPES',
    'SYSTEM_SCOPE',
    'USER_SCOPE',
    'USER_SEPARATOR',

    'DATASTORE_KEY_SEPARATOR'
]

# Namespace to contain all system/global scoped variables in key-value store.
SYSTEM_SCOPE = 'system'

# Namespace to contain all user scoped variables in key-value store.
USER_SCOPE = 'user'

USER_SEPARATOR = ':'

ALLOWED_SCOPES = [
    SYSTEM_SCOPE,
    USER_SCOPE
]

# Separator for keys in the datastore
DATASTORE_KEY_SEPARATOR = ':'
