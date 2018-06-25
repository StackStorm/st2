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

import mock

import unittest2

from functions.st2kv import st2kv_


TEST_CONTEXT = {
    '__vars': {
        'st2': {
            'user': 'stanley'
        }
    }
}


class TestST2KV(unittest2.TestCase):
    @mock.patch('functions.st2kv.get_key')
    def test_valid_return(self, get_name):
        key = 'test'
        get_name.return_value = key

        result = st2kv_(TEST_CONTEXT, key)

        self.assertEquals(key, result)

    @mock.patch('functions.st2kv.get_key')
    def test_key_error(self, get_name):
        key = 'test'
        get_name.return_value = key

        self.assertRaises(KeyError, st2kv_, {}, key)

    def test_invalid_input(self):
        self.assertRaises(TypeError, st2kv_, None, 123)
        self.assertRaises(TypeError, st2kv_, {}, 123)
        self.assertRaises(TypeError, st2kv_, {}, dict())
        self.assertRaises(TypeError, st2kv_, {}, object())
        self.assertRaises(TypeError, st2kv_, {}, [1, 2])
