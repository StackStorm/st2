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

from __future__ import absolute_import

from oslo_config import cfg

from st2common.services.keyvalues import KeyValueLookup
from st2common.services.keyvalues import UserKeyValueLookup
from st2common.constants.keyvalue import DATASTORE_PARENT_SCOPE
from st2common.constants.keyvalue import SYSTEM_SCOPE
from st2common.constants.keyvalue import USER_SCOPE
from st2common.util.crypto import read_crypto_key, symmetric_decrypt

__all__ = [
    'decrypt_kv'
]


def decrypt_kv(value):
    original_value = value

    if isinstance(value, KeyValueLookup) or isinstance(value, UserKeyValueLookup):
        # Since this is a filter the incoming value is still a KeyValueLookup
        # object as the jinja rendering is not yet complete. So we cast
        # the KeyValueLookup object to a simple string before decrypting.
        is_kv_item = True
        value = str(value)
    else:
        is_kv_item = False

    # NOTE: If value is None this indicate key value item doesn't exist and we hrow a more
    # user-friendly error
    if is_kv_item and value == '':
        # Build original key name
        key_name_parts = [DATASTORE_PARENT_SCOPE]

        if isinstance(original_value, KeyValueLookup):
            key_name_parts.append(SYSTEM_SCOPE)
        elif isinstance(original_value, UserKeyValueLookup):
            key_name_parts.append(USER_SCOPE)

        key_name = original_value.__dict__.get('_key_prefix').split(':', 1)

        if len(key_name) == 1:
            key_name = key_name[0]
        else:
            key_name = key_name[1]

        key_name_parts.append(key_name)
        key_name = '.'.join(key_name_parts)

        raise ValueError('Referenced datastore item "%s" doesn\'t exist' % (key_name))

    crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
    crypto_key = read_crypto_key(key_path=crypto_key_path)
    return symmetric_decrypt(decrypt_key=crypto_key, ciphertext=value)
