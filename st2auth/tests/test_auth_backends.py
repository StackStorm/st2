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

import os

import unittest2

from st2auth.backends.flat_file import FlatFileAuthenticationBackend
from st2auth.backends.mongodb import MongoDBAuthenticationBackend

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class FlatFileAuthenticationBackendTestCase(unittest2.TestCase):
    def test_authenticate(self):
        file_path = os.path.join(BASE_DIR, 'fixtures/htpasswd_test')
        backend = FlatFileAuthenticationBackend(file_path=file_path)

        # Inexistent user
        self.assertFalse(backend.authenticate(username='doesntexist', password='bar'))

        # Invalid password
        self.assertFalse(backend.authenticate(username='test1', password='bar'))

        # Valid password (md5 hash)
        self.assertTrue(backend.authenticate(username='test1', password='testpassword'))

        # Valid password (sha hash - insecure)
        self.assertTrue(backend.authenticate(username='test3', password='testpassword'))

        # Valid password (crypt - insecure)
        self.assertTrue(backend.authenticate(username='test4', password='testpassword'))


class MongoDBAuthenticationBackendTestCase(unittest2.TestCase):
    hash_function = MongoDBAuthenticationBackend._hash_function
    fixtures = [
        {
            'username': 'test1',
            'salt': 'salty',
            'password': hash_function('saltytestpassword').hexdigest()
        }
    ]

    def setUp(self):
        self._backend = MongoDBAuthenticationBackend(db_name='st2authtest')

        # Clear database
        self._backend._collection.remove()

        # Add fixtures
        for fixture in self.fixtures:
            self._backend._collection.insert(fixture)

    def tearDown(self):
        # Clear database
        self._backend._collection.remove()

    def test_authenticate(self):
        # Inexistent user
        self.assertFalse(self._backend.authenticate(username='inexistent', password='ponies'))

        # Existent user, invalid password
        self.assertFalse(self._backend.authenticate(username='test1', password='ponies'))

        # Valid password
        self.assertTrue(self._backend.authenticate(username='test1', password='testpassword'))
