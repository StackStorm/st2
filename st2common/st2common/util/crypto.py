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
import binascii

__all__ = [
    'read_crypto_key',
    'symmetric_encrypt',
    'symmetric_decrypt'
]


def read_crypto_key(key_path, key_type=None):
    """
    Return the crypto key given a path to key file and the key type.

    :param key_path: Absolute path to file containing crypto key.
    :type key_path: ``str``

    :param key_type: Type of crypto key.
    :type key_type: :class:`keyczar.keys.KeyType`

    :rtype: ``str``
    """

    # Late import to avoid very expensive in-direct import (~1 second) when this function
    # is not called / used
    from keyczar.keys import AesKey
    key_type = key_type or AesKey

    with open(key_path) as key_file:
        key = key_type.Read(key_file.read())
        return key


def symmetric_encrypt(encrypt_key, plaintext):
    """
    Encrypt the given message using the encrypt_key. Returns a UTF-8 str
    ready to be stored in database. Note that we convert the hex notation
    to a ASCII notation to produce a UTF-8 friendly string.

    Also, this method will not return the same output on multiple invocations
    of same method. The reason is that the Encrypt method uses a different
    'Initialization Vector' per run and the IV is part of the output.

    :param encrypt_key: Symmetric AES key to use for encryption.
    :type encrypt_key: :class:`keyczar.keys.AesKey`

    :param plaintext: Plaintext / message to be encrypted.
    :type plaintext: ``str``

    :rtype: ``str``
    """
    return binascii.hexlify(encrypt_key.Encrypt(plaintext)).upper()


def symmetric_decrypt(decrypt_key, ciphertext):
    """
    Decrypt the given crypto text into plain text. Returns the original
    string input. Note that we first convert the string to hex notation
    and then decrypt. This is reverse of the encrypt operation.

    :param decrypt_key: Symmetric AES key to use for decryption.
    :type decrypt_key: :class:`keyczar.keys.AesKey`

    :param crypto: Crypto text to be decrypted.
    :type crypto: ``str``

    :rtype: ``str``
    """
    return decrypt_key.Decrypt(binascii.unhexlify(ciphertext))
