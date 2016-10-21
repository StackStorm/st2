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

from oslo_config import cfg

from st2common.services.keyvalues import KeyValueLookup
from st2common.util.crypto import read_crypto_key, symmetric_decrypt

__all__ = [
    'decrypt_kv'
]


def decrypt_kv(value):
    if isinstance(value, KeyValueLookup):
        # Since this is a filter the incoming value is still a KeyValueLookup
        # object as the jinja rendering is not yet complete. So we cast
        # the KeyValueLookup object to a simple string before decrypting.
        value = str(value)
    crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
    crypto_key = read_crypto_key(key_path=crypto_key_path)
    return symmetric_decrypt(decrypt_key=crypto_key, ciphertext=value)
