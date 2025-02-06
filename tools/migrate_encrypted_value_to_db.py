#!/usr/bin/env python

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

from mongoengine.queryset import Q
import binascii

from hashlib import sha1
import six

from st2common import config
from st2common.script_setup import setup as db_setup
from st2common.script_setup import teardown as db_teardown
from st2common.persistence.keyvalue import KeyValuePair
from st2common.models.db.keyvalue import KeyValuePairDB

from st2common.util.crypto import AESKey
from st2common.util.crypto import symmetric_encrypt
from st2common.util.crypto import read_crypto_key
from st2common.util.crypto import Base64WSDecode
from st2common.util.crypto import pkcs5_unpad


from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import hmac
from cryptography.hazmat.backends import default_backend

# Keyczar related constants
KEYCZAR_HEADER_SIZE = 5
KEYCZAR_AES_BLOCK_SIZE = 16
KEYCZAR_HLEN = sha1().digest_size


class EncryptedValueMigration(object):
    def _get_keyvalue_with_parameters(self):
        """
        All KeyValueDB that has a secret parameter.
        """
        return KeyValuePairDB.objects(Q(secret=True))

    def migrate_encrypted_value(self):
        """
        Will migrate the new encrypted value to KeyValuePair.
        """
        keyvalue_dbs = self._get_keyvalue_with_parameters()
        crypto_key_path = cfg.CONF.keyvalue.encryption_key_path
        crypto_key = read_crypto_key(crypto_key_path)
        hmac_key_bytes = Base64WSDecode(crypto_key.hmac_key_string)
        aes_key_bytes = Base64WSDecode(crypto_key.aes_key_string)
        for keyvalue_db in keyvalue_dbs:
            if keyvalue_db.secret:
                plaintext = cryptography_symmetric_decrypt(
                    hmac_key_bytes, aes_key_bytes, keyvalue_db.value
                )
                crypto_key = AESKey.generate()
                new_encrypted_value = symmetric_encrypt(crypto_key, plaintext)
                new_encrypted_value = str(new_encrypted_value)
                keyvalue_db.new_encrypted_value = new_encrypted_value[2:-1]
                KeyValuePair.add_or_update(keyvalue_db)
                print(
                    "Updated encrypted value. "
                    f"key={keyvalue_db.name} new_encrypted_value={new_encrypted_value}"
                )
            else:
                print(
                    "Unexpected cleartext value in query for secret datastore values. "
                    f"key={keyvalue_db.name}"
                )


def setup():
    db_setup(config=config, setup_db=True)


def teardown():
    db_teardown()


def cryptography_symmetric_decrypt(hmac_key_bytes, aes_key_bytes, ciphertext):
    """
    Decrypt the provided ciphertext which has been encrypted using symmetric_encrypt() method (it
    assumes input is in hex notation as returned by binascii.hexlify).


    NOTE 1: This function assumes ciphertext has been encrypted using symmetric AES crypto from
    keyczar library. Underneath it uses crypto primitives from cryptography library which is Python
    3 compatible.


    NOTE 2: This function is loosely based on keyczar AESKey.Decrypt() (Apache 2.0 license).
    """

    if not isinstance(aes_key_bytes, six.binary_type):
        raise TypeError("Key Bytes type not matching")
    if not isinstance(hmac_key_bytes, six.binary_type):
        raise TypeError("Value Type not matching")

    # Convert from hex notation ASCII string to bytes
    ciphertext = binascii.unhexlify(ciphertext)

    data_bytes = ciphertext[KEYCZAR_HEADER_SIZE:]  # remove header

    # Verify ciphertext contains IV + HMAC signature
    if len(data_bytes) < (KEYCZAR_AES_BLOCK_SIZE + KEYCZAR_HLEN):
        raise ValueError("Invalid or malformed ciphertext (too short)")

    iv_bytes = data_bytes[:KEYCZAR_AES_BLOCK_SIZE]  # first block is IV
    ciphertext_bytes = data_bytes[
        KEYCZAR_AES_BLOCK_SIZE:-KEYCZAR_HLEN
    ]  # strip IV and signature
    signature_bytes = data_bytes[-KEYCZAR_HLEN:]  # last 20 bytes are signature

    # Verify HMAC signature
    backend = default_backend()
    h = hmac.HMAC(hmac_key_bytes, hashes.SHA1(), backend=backend)
    h.update(ciphertext[:-KEYCZAR_HLEN])
    h.verify(signature_bytes)

    # Decrypt ciphertext
    cipher = Cipher(algorithms.AES(aes_key_bytes), modes.CBC(iv_bytes), backend=backend)

    decryptor = cipher.decryptor()
    decrypted = decryptor.update(ciphertext_bytes) + decryptor.finalize()

    # Unpad
    decrypted = pkcs5_unpad(decrypted)
    return decrypted


def main():

    config.parse_args()

    # Connect to database
    setup()

    try:
        EncryptedValueMigration().migrate_encrypted_value()
        print("SUCCESS: Encrypyted value migrated successfully.")
    except Exception as e:
        print("ABORTED: Encrypyted value migration aborted on first failure.", {e})
    finally:

        # Disconnect from db.
        teardown()


if __name__ == "__main__":
    main()
