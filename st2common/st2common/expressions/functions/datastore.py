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

from __future__ import absolute_import

from oslo_config import cfg

from st2common.services.keyvalues import KeyValueLookup
from st2common.services.keyvalues import UserKeyValueLookup
from st2common.util.crypto import read_crypto_key
from st2common.util.crypto import symmetric_decrypt

__all__ = ["decrypt_kv"]


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
    if is_kv_item and value == "":
        # Build original key name
        key_name = original_value.get_key_name()
        raise ValueError(
            'Referenced datastore item "%s" doesn\'t exist or it contains an empty '
            "string" % (key_name)
        )

    crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
    crypto_key = read_crypto_key(key_path=crypto_key_path)
    return symmetric_decrypt(decrypt_key=crypto_key, ciphertext=value)
