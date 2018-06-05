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

from __future__ import absolute_import

import six
import json

import unittest2
from unittest2 import TestCase

from st2common.util.crypto import AESKey
from st2common.util.crypto import symmetric_encrypt
from st2common.util.crypto import symmetric_decrypt
from st2common.util.crypto import keyczar_symmetric_decrypt
from st2common.util.crypto import keyczar_symmetric_encrypt
from st2common.util.crypto import cryptography_symmetric_encrypt
from st2common.util.crypto import cryptography_symmetric_decrypt

from six.moves import range

__all__ = [
    'CryptoUtilsTestCase',
    'CryptoUtilsKeyczarCompatibilityTestCase'
]


class CryptoUtilsTestCase(TestCase):

    @classmethod
    def setUpClass(cls):
        super(CryptoUtilsTestCase, cls).setUpClass()
        CryptoUtilsTestCase.test_crypto_key = AESKey.generate()

    def test_symmetric_encrypt_decrypt(self):
        original = 'secret'
        crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
        plain = symmetric_decrypt(CryptoUtilsTestCase.test_crypto_key, crypto)
        self.assertEqual(plain, original)

    def test_encrypt_output_is_diff_due_to_diff_IV(self):
        original = 'Kami is a little boy.'
        cryptos = set()

        for _ in range(0, 10000):
            crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
            self.assertTrue(crypto not in cryptos)
            cryptos.add(crypto)


class CryptoUtilsKeyczarCompatibilityTestCase(TestCase):
    """
    Tests which verify that new cryptography based symmetric_encrypt and symmetric_decrypt are
    fully compatible with keyczar output format and also return keyczar based format.
    """

    def test_key_generation_file_format_is_fully_keyczar_compatible(self):
        # Verify that the code can read and correctly parse keyczar formatted key files
        aes_key = AESKey.generate()
        key_json = aes_key.__json__()
        json_parsed = json.loads(key_json)

        expected = {
            'hmacKey': {
                'hmacKeyString': aes_key.hmac_key_string,
                'size': aes_key.hmac_key_size
            },
            'aesKeyString': aes_key.aes_key_string,
            'mode': aes_key.mode,
            'size': aes_key.size
        }

        self.assertEqual(json_parsed, expected)

    def test_symmetric_encrypt_decrypt_cryptography(self):
        key = AESKey.generate()
        plaintexts = [
            'a b c',
            'ab',
            'hello foo',
            'hell',
            'bar5'
            'hello hello bar bar hello',
            'a',
            '',
            'c'
        ]

        for plaintext in plaintexts:
            encrypted = cryptography_symmetric_encrypt(key, plaintext)
            decrypted = cryptography_symmetric_decrypt(key, encrypted)

            self.assertEqual(decrypted, plaintext)

    @unittest2.skipIf(six.PY3, 'keyczar doesn\'t work under Python 3')
    def test_symmetric_encrypt_decrypt_roundtrips_1(self):
        encrypt_keys = [
            AESKey.generate(),
            AESKey.generate(),
            AESKey.generate(),
            AESKey.generate()
        ]

        # Verify all keys are unique
        aes_key_strings = set()
        hmac_key_strings = set()

        for key in encrypt_keys:
            aes_key_strings.add(key.aes_key_string)
            hmac_key_strings.add(key.hmac_key_string)

        self.assertEqual(len(aes_key_strings), 4)
        self.assertEqual(len(hmac_key_strings), 4)

        plaintext = 'hello world test dummy 8 9 5 1 bar2'

        # Verify that round trips work and that cryptography based primitives are fully compatible
        # with keyczar format

        count = 0
        for key in encrypt_keys:
            data_enc_keyczar = keyczar_symmetric_encrypt(key, plaintext)
            data_enc_cryptography = cryptography_symmetric_encrypt(key, plaintext)

            self.assertNotEqual(data_enc_keyczar, data_enc_cryptography)

            data_dec_keyczar_keyczar = keyczar_symmetric_decrypt(key, data_enc_keyczar)
            data_dec_keyczar_cryptography = keyczar_symmetric_decrypt(key, data_enc_cryptography)

            self.assertEqual(data_dec_keyczar_keyczar, plaintext)
            self.assertEqual(data_dec_keyczar_cryptography, plaintext)

            data_dec_cryptography_cryptography = cryptography_symmetric_decrypt(key,
                data_enc_cryptography)
            data_dec_cryptography_keyczar = cryptography_symmetric_decrypt(key, data_enc_keyczar)

            self.assertEqual(data_dec_cryptography_cryptography, plaintext)
            self.assertEqual(data_dec_cryptography_keyczar, plaintext)

            count += 1

        self.assertEqual(count, 4)
