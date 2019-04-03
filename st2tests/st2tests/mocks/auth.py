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

from st2auth.backends.base import BaseAuthenticationBackend

# auser:apassword in b64
DUMMY_CREDS = 'YXVzZXI6YXBhc3N3b3Jk'

__all__ = [
    'DUMMY_CREDS',

    'MockAuthBackend',
    'MockRequest',

    'get_mock_backend'
]


class MockAuthBackend(BaseAuthenticationBackend):
    groups = []

    def authenticate(self, username, password):
        return ((username == 'auser' and password == 'apassword') or
                (username == 'username' and password == 'password:password'))

    def get_user(self, username):
        return username

    def get_user_groups(self, username):
        return self.groups


class MockRequest():
    def __init__(self, ttl):
        self.ttl = ttl

    user = None
    ttl = None
    impersonate_user = None
    nickname_origin = None


def get_mock_backend(name):
    return MockAuthBackend()
