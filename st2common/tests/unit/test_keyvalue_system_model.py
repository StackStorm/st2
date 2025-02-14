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
import unittest

from st2common.models.system.keyvalue import InvalidUserKeyReferenceError
from st2common.models.system.keyvalue import UserKeyReference


class UserKeyReferenceSystemModelTest(unittest.TestCase):
    def test_to_string_reference(self):
        key_ref = UserKeyReference.to_string_reference(user="stanley", name="foo")
        self.assertEqual(key_ref, "stanley:foo")
        self.assertRaises(
            ValueError, UserKeyReference.to_string_reference, user=None, name="foo"
        )

    def test_from_string_reference(self):
        user, name = UserKeyReference.from_string_reference("stanley:foo")
        self.assertEqual(user, "stanley")
        self.assertEqual(name, "foo")
        self.assertRaises(
            InvalidUserKeyReferenceError,
            UserKeyReference.from_string_reference,
            "this_key_has_no_sep",
        )
