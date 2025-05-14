# -*- coding: utf-8 -*-

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

import os

import six
import json
import binascii

import pytest
from unittest import TestCase
from six.moves import range
from cryptography.exceptions import InvalidSignature

from st2common.util.crypto import KEYCZAR_HEADER_SIZE
from st2common.util.crypto import AESKey
from st2common.util.crypto import read_crypto_key
from st2common.util.crypto import symmetric_encrypt
from st2common.util.crypto import symmetric_decrypt
from st2common.util.crypto import keyczar_symmetric_decrypt
from st2common.util.crypto import keyczar_symmetric_encrypt
from st2common.util.crypto import cryptography_symmetric_encrypt
from st2common.util.crypto import cryptography_symmetric_decrypt

from st2tests.fixtures.keyczar_keys.fixture import FIXTURE_PATH as KEY_FIXTURES_PATH

__all__ = ["CryptoUtilsTestCase", "CryptoUtilsKeyczarCompatibilityTestCase"]


class CryptoUtilsTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super(CryptoUtilsTestCase, cls).setUpClass()
        CryptoUtilsTestCase.test_crypto_key = AESKey.generate()

    def test_symmetric_encrypt_decrypt_short_string_needs_to_be_padded(self):
        original = "a"
        crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
        plain = symmetric_decrypt(CryptoUtilsTestCase.test_crypto_key, crypto)
        self.assertEqual(plain, original)

    def test_symmetric_encrypt_decrypt_utf8_character(self):
        values = [
            "£",
            "£££",
            "££££££",
            "č š hello đ č p ž Ž",
            "hello 💩",
            "💩💩💩💩💩" "💩💩💩",
            "💩😁",
        ]

        for index, original in enumerate(values):
            crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
            plain = symmetric_decrypt(CryptoUtilsTestCase.test_crypto_key, crypto)
            self.assertEqual(plain, original)

        self.assertEqual(index, (len(values) - 1))

    def test_symmetric_encrypt_decrypt(self):
        original = "secret"
        crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
        plain = symmetric_decrypt(CryptoUtilsTestCase.test_crypto_key, crypto)
        self.assertEqual(plain, original)

    def test_encrypt_output_is_diff_due_to_diff_IV(self):
        original = "Kami is a little boy."
        cryptos = set()

        for _ in range(0, 10000):
            crypto = symmetric_encrypt(CryptoUtilsTestCase.test_crypto_key, original)
            self.assertNotIn(crypto, cryptos)
            cryptos.add(crypto)

    def test_decrypt_ciphertext_is_too_short(self):
        aes_key = AESKey.generate()
        plaintext = "hello world ponies 1"
        encrypted = cryptography_symmetric_encrypt(aes_key, plaintext)

        # Verify original non manipulated value can be decrypted
        decrypted = cryptography_symmetric_decrypt(aes_key, encrypted)
        self.assertEqual(decrypted, plaintext)

        # Corrupt / shortern the encrypted data
        encrypted_malformed = binascii.unhexlify(encrypted)
        header = encrypted_malformed[:KEYCZAR_HEADER_SIZE]
        encrypted_malformed = encrypted_malformed[KEYCZAR_HEADER_SIZE:]

        # Remove 40 bytes from ciphertext bytes
        encrypted_malformed = encrypted_malformed[40:]

        # Add back header
        encrypted_malformed = header + encrypted_malformed
        encrypted_malformed = binascii.hexlify(encrypted_malformed)

        # Verify corrupted value results in an excpetion
        expected_msg = "Invalid or malformed ciphertext"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            cryptography_symmetric_decrypt,
            aes_key,
            encrypted_malformed,
        )

    def test_exception_is_thrown_on_invalid_hmac_signature(self):
        aes_key = AESKey.generate()
        plaintext = "hello world ponies 2"
        encrypted = cryptography_symmetric_encrypt(aes_key, plaintext)

        # Verify original non manipulated value can be decrypted
        decrypted = cryptography_symmetric_decrypt(aes_key, encrypted)
        self.assertEqual(decrypted, plaintext)

        # Corrupt the HMAC signature (last part is the HMAC signature)
        encrypted_malformed = binascii.unhexlify(encrypted)
        encrypted_malformed = encrypted_malformed[:-3]
        encrypted_malformed += b"abc"
        encrypted_malformed = binascii.hexlify(encrypted_malformed)

        # Verify corrupted value results in an excpetion
        expected_msg = "Signature did not match digest"
        self.assertRaisesRegex(
            InvalidSignature,
            expected_msg,
            cryptography_symmetric_decrypt,
            aes_key,
            encrypted_malformed,
        )


class CryptoUtilsKeyczarCompatibilityTestCase(TestCase):
    """
    Tests which verify that new cryptography based symmetric_encrypt and symmetric_decrypt are
    fully compatible with keyczar output format and also return keyczar based format.
    """

    def test_aes_key_class(self):
        # 1. Unsupported mode
        expected_msg = "Unsupported mode: EBC"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            AESKey,
            aes_key_string="a",
            hmac_key_string="b",
            hmac_key_size=128,
            mode="EBC",
        )

        # 2. AES key is too small
        expected_msg = "Unsafe key size: 64"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            AESKey,
            aes_key_string="a",
            hmac_key_string="b",
            hmac_key_size=128,
            mode="CBC",
            size=64,
        )

    def test_loading_keys_from_keyczar_formatted_key_files(self):
        key_path = os.path.join(KEY_FIXTURES_PATH, "one.json")
        aes_key = read_crypto_key(key_path=key_path)

        self.assertEqual(
            aes_key.hmac_key_string, "lgI9YdOKlIOtPQFdgB0B6zr0AZ6L2QJuFQg4gTu2dxc"
        )
        self.assertEqual(aes_key.hmac_key_size, 256)

        self.assertEqual(
            aes_key.aes_key_string, "vKmBE2YeQ9ATyovel7NDjdnbvOMcoU5uPtUVxWxWm58"
        )
        self.assertEqual(aes_key.mode, "CBC")
        self.assertEqual(aes_key.size, 256)

        key_path = os.path.join(KEY_FIXTURES_PATH, "two.json")
        aes_key = read_crypto_key(key_path=key_path)

        self.assertEqual(
            aes_key.hmac_key_string, "92ok9S5extxphADmUhObPSD5wugey8eTffoJ2CEg_2s"
        )
        self.assertEqual(aes_key.hmac_key_size, 256)

        self.assertEqual(
            aes_key.aes_key_string, "fU9hT9pm-b9hu3VyQACLXe2Z7xnaJMZrXiTltyLUzgs"
        )
        self.assertEqual(aes_key.mode, "CBC")
        self.assertEqual(aes_key.size, 256)

        key_path = os.path.join(KEY_FIXTURES_PATH, "five.json")
        aes_key = read_crypto_key(key_path=key_path)

        self.assertEqual(
            aes_key.hmac_key_string, "GCX2uMfOzp1JXYgqH8piEE4_mJOPXydH_fRHPDw9bkM"
        )
        self.assertEqual(aes_key.hmac_key_size, 256)

        self.assertEqual(aes_key.aes_key_string, "EeBcUcbH14tL0w_fF5siEw")
        self.assertEqual(aes_key.mode, "CBC")
        self.assertEqual(aes_key.size, 128)

    def test_key_generation_file_format_is_fully_keyczar_compatible(self):
        # Verify that the code can read and correctly parse keyczar formatted key files
        aes_key = AESKey.generate()
        key_json = aes_key.to_json()
        json_parsed = json.loads(key_json)

        expected = {
            "hmacKey": {
                "hmacKeyString": aes_key.hmac_key_string,
                "size": aes_key.hmac_key_size,
            },
            "aesKeyString": aes_key.aes_key_string,
            "mode": aes_key.mode,
            "size": aes_key.size,
        }

        self.assertEqual(json_parsed, expected)

    def test_symmetric_encrypt_decrypt_cryptography(self):
        key = AESKey.generate()
        plaintexts = [
            "a b c",
            "ab",
            "hello foo",
            "hell",
            "bar5" "hello hello bar bar hello",
            "a",
            "",
            "c",
        ]

        for plaintext in plaintexts:
            encrypted = cryptography_symmetric_encrypt(key, plaintext)
            decrypted = cryptography_symmetric_decrypt(key, encrypted)

            self.assertEqual(decrypted, plaintext)

    @pytest.mark.skipif(six.PY3, reason="keyczar doesn't work under Python 3")
    def test_symmetric_encrypt_decrypt_roundtrips_1(self):
        encrypt_keys = [
            AESKey.generate(),
            AESKey.generate(),
            AESKey.generate(),
            AESKey.generate(),
        ]

        # Verify all keys are unique
        aes_key_strings = set()
        hmac_key_strings = set()

        for key in encrypt_keys:
            aes_key_strings.add(key.aes_key_string)
            hmac_key_strings.add(key.hmac_key_string)

        self.assertEqual(len(aes_key_strings), 4)
        self.assertEqual(len(hmac_key_strings), 4)

        plaintext = "hello world test dummy 8 9 5 1 bar2"

        # Verify that round trips work and that cryptography based primitives are fully compatible
        # with keyczar format

        count = 0
        for key in encrypt_keys:
            data_enc_keyczar = keyczar_symmetric_encrypt(key, plaintext)
            data_enc_cryptography = cryptography_symmetric_encrypt(key, plaintext)

            self.assertNotEqual(data_enc_keyczar, data_enc_cryptography)

            data_dec_keyczar_keyczar = keyczar_symmetric_decrypt(key, data_enc_keyczar)
            data_dec_keyczar_cryptography = keyczar_symmetric_decrypt(
                key, data_enc_cryptography
            )

            self.assertEqual(data_dec_keyczar_keyczar, plaintext)
            self.assertEqual(data_dec_keyczar_cryptography, plaintext)

            data_dec_cryptography_cryptography = cryptography_symmetric_decrypt(
                key, data_enc_cryptography
            )
            data_dec_cryptography_keyczar = cryptography_symmetric_decrypt(
                key, data_enc_keyczar
            )

            self.assertEqual(data_dec_cryptography_cryptography, plaintext)
            self.assertEqual(data_dec_cryptography_keyczar, plaintext)

            count += 1

        self.assertEqual(count, 4)
