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

import unittest2

from st2common.models.system.common import ResourceReference
from st2common.models.system.common import InvalidResourceReferenceError


class ResourceReferenceTestCase(unittest2.TestCase):
    def test_resource_reference_success(self):
        value = 'pack1.name1'
        ref = ResourceReference.from_string_reference(ref=value)

        self.assertEqual(ref.pack, 'pack1')
        self.assertEqual(ref.name, 'name1')
        self.assertEqual(ref.ref, value)

        ref = ResourceReference(pack='pack1', name='name1')
        self.assertEqual(ref.ref, 'pack1.name1')

        ref = ResourceReference(pack='pack1', name='name1.name2')
        self.assertEqual(ref.ref, 'pack1.name1.name2')

    def test_resource_reference_failure(self):
        self.assertRaises(InvalidResourceReferenceError,
                          ResourceReference.from_string_reference,
                          ref='blah')

        self.assertRaises(InvalidResourceReferenceError,
                          ResourceReference.from_string_reference,
                          ref=None)

    def test_to_string_reference(self):
        ref = ResourceReference.to_string_reference(pack='mapack', name='moname')
        self.assertEqual(ref, 'mapack.moname')

        expected_msg = 'Pack name should not contain "\."'
        self.assertRaisesRegexp(ValueError, expected_msg, ResourceReference.to_string_reference,
                                pack='pack.invalid', name='bar')

        expected_msg = 'Both pack and name needed for building'
        self.assertRaisesRegexp(ValueError, expected_msg, ResourceReference.to_string_reference,
                                pack='pack', name=None)

        expected_msg = 'Both pack and name needed for building'
        self.assertRaisesRegexp(ValueError, expected_msg, ResourceReference.to_string_reference,
                                pack=None, name='name')

    def test_is_resource_reference(self):
        self.assertTrue(ResourceReference.is_resource_reference('foo.bar'))
        self.assertTrue(ResourceReference.is_resource_reference('foo.bar.ponies'))
        self.assertFalse(ResourceReference.is_resource_reference('foo'))
