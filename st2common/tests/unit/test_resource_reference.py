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

from st2common.models.system.common import ResourceReference
from st2common.models.system.common import InvalidResourceReferenceError


class ResourceReferenceTestCase(unittest.TestCase):
    def test_resource_reference_success(self):
        value = "pack1.name1"
        ref = ResourceReference.from_string_reference(ref=value)

        self.assertEqual(ref.pack, "pack1")
        self.assertEqual(ref.name, "name1")
        self.assertEqual(ref.ref, value)

        ref = ResourceReference(pack="pack1", name="name1")
        self.assertEqual(ref.ref, "pack1.name1")

        ref = ResourceReference(pack="pack1", name="name1.name2")
        self.assertEqual(ref.ref, "pack1.name1.name2")

    def test_resource_reference_failure(self):
        self.assertRaises(
            InvalidResourceReferenceError,
            ResourceReference.from_string_reference,
            ref="blah",
        )

        self.assertRaises(
            InvalidResourceReferenceError,
            ResourceReference.from_string_reference,
            ref=None,
        )

    def test_to_string_reference(self):
        ref = ResourceReference.to_string_reference(pack="mapack", name="moname")
        self.assertEqual(ref, "mapack.moname")

        expected_msg = r'Pack name should not contain "\."'
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            ResourceReference.to_string_reference,
            pack="pack.invalid",
            name="bar",
        )

        expected_msg = "Both pack and name needed for building"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            ResourceReference.to_string_reference,
            pack="pack",
            name=None,
        )

        expected_msg = "Both pack and name needed for building"
        self.assertRaisesRegex(
            ValueError,
            expected_msg,
            ResourceReference.to_string_reference,
            pack=None,
            name="name",
        )

    def test_is_resource_reference(self):
        self.assertTrue(ResourceReference.is_resource_reference("foo.bar"))
        self.assertTrue(ResourceReference.is_resource_reference("foo.bar.ponies"))
        self.assertFalse(ResourceReference.is_resource_reference("foo"))
