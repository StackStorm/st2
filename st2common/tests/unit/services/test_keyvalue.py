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
import unittest2

from st2common.constants.keyvalue import SYSTEM_SCOPE, USER_SCOPE
from st2common.exceptions.keyvalue import InvalidScopeException, InvalidUserException
from st2common.services.keyvalues import get_key_reference


class KeyValueServicesTest(unittest2.TestCase):
    def test_get_key_reference_system_scope(self):
        ref = get_key_reference(scope=SYSTEM_SCOPE, name="foo")
        self.assertEqual(ref, "foo")

    def test_get_key_reference_user_scope(self):
        ref = get_key_reference(scope=USER_SCOPE, name="foo", user="stanley")
        self.assertEqual(ref, "stanley:foo")
        self.assertRaises(
            InvalidUserException,
            get_key_reference,
            scope=USER_SCOPE,
            name="foo",
            user="",
        )

    def test_get_key_reference_invalid_scope_raises_exception(self):
        self.assertRaises(
            InvalidScopeException, get_key_reference, scope="sketchy", name="foo"
        )
