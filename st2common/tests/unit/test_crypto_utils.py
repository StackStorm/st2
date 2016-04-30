# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the 'License'); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from keyczar.keys import AesKey
from unittest2 import TestCase


import st2common.util.crypto as crypto_utils


class CryptoUtilsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(CryptoUtilsTestCase, cls).setUpClass()
        CryptoUtilsTestCase.test_crypto_key = AesKey.Generate()

    def test_symmetric_encrypt_decrypt(self):
        original = 'secret'
        crypto = crypto_utils.symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
        plain = crypto_utils.symmetric_decrypt(CryptoUtilsTestCase.test_crypto_key, crypto)
        self.assertEqual(plain, original)

    def test_encrypt_output_is_diff_due_to_diff_IV(self):
        original = 'Kami is a little boy.'
        cryptos = set()

        for _ in xrange(0, 10000):
            crypto = crypto_utils.symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key,
                                                    original)
            self.assertTrue(crypto not in cryptos)
            cryptos.add(crypto)
