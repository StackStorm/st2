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

from st2tests.base import CleanDbTestCase
from st2common.constants.keyvalue import FULL_SYSTEM_SCOPE, SYSTEM_SCOPE, DATASTORE_PARENT_SCOPE
from st2common.models.db.keyvalue import KeyValuePairDB
from st2common.persistence.keyvalue import KeyValuePair
from st2common.services.keyvalues import KeyValueLookup
from st2common.util import jinja as jinja_utils
from st2common.util.crypto import read_crypto_key, symmetric_encrypt


class JinjaUtilsDecryptTestCase(CleanDbTestCase):

    def test_filter_decrypt_kv(self):
        secret = 'Build a wall'
        crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
        crypto_key = read_crypto_key(key_path=crypto_key_path)
        secret_value = symmetric_encrypt(encrypt_key=crypto_key, plaintext=secret)
        KeyValuePair.add_or_update(KeyValuePairDB(name='k8', value=secret_value,
                                                  scope=FULL_SYSTEM_SCOPE,
                                                  secret=True))
        env = jinja_utils.get_jinja_environment()

        context = {}
        context.update({SYSTEM_SCOPE: KeyValueLookup(scope=SYSTEM_SCOPE)})
        context.update({
            DATASTORE_PARENT_SCOPE: {
                SYSTEM_SCOPE: KeyValueLookup(scope=FULL_SYSTEM_SCOPE)
            }
        })

        template = '{{st2kv.system.k8 | decrypt_kv}}'
        actual = env.from_string(template).render(context)
        self.assertEqual(actual, secret)
