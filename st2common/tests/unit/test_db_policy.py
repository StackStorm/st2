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

from st2common.constants import pack as pack_constants
from st2common.models.db.policy import PolicyTypeReference, PolicyTypeDB, PolicyDB
from st2common.models.system.common import InvalidReferenceError
from st2common.persistence.policy import PolicyType, Policy
from st2tests import DbModelTestCase


class PolicyTypeReferenceTest(unittest.TestCase):
    def test_is_reference(self):
        self.assertTrue(PolicyTypeReference.is_reference("action.concurrency"))
        self.assertFalse(PolicyTypeReference.is_reference("concurrency"))
        self.assertFalse(PolicyTypeReference.is_reference(""))
        self.assertFalse(PolicyTypeReference.is_reference(None))

    def test_validate_resource_type(self):
        self.assertEqual(PolicyTypeReference.validate_resource_type("action"), "action")
        self.assertRaises(
            ValueError, PolicyTypeReference.validate_resource_type, "action.test"
        )

    def test_get_resource_type(self):
        self.assertEqual(
            PolicyTypeReference.get_resource_type("action.concurrency"), "action"
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.get_resource_type, ".abc"
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.get_resource_type, "abc"
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.get_resource_type, ""
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.get_resource_type, None
        )

    def test_get_name(self):
        self.assertEqual(
            PolicyTypeReference.get_name("action.concurrency"), "concurrency"
        )
        self.assertRaises(InvalidReferenceError, PolicyTypeReference.get_name, ".abc")
        self.assertRaises(InvalidReferenceError, PolicyTypeReference.get_name, "abc")
        self.assertRaises(InvalidReferenceError, PolicyTypeReference.get_name, "")
        self.assertRaises(InvalidReferenceError, PolicyTypeReference.get_name, None)

    def test_to_string_reference(self):
        ref = PolicyTypeReference.to_string_reference(
            resource_type="action", name="concurrency"
        )
        self.assertEqual(ref, "action.concurrency")

        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type="action.test",
            name="concurrency",
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type=None,
            name="concurrency",
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type="",
            name="concurrency",
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type="action",
            name=None,
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type="action",
            name="",
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type=None,
            name=None,
        )
        self.assertRaises(
            ValueError,
            PolicyTypeReference.to_string_reference,
            resource_type="",
            name="",
        )

    def test_from_string_reference(self):
        ref = PolicyTypeReference.from_string_reference("action.concurrency")
        self.assertEqual(ref.resource_type, "action")
        self.assertEqual(ref.name, "concurrency")
        self.assertEqual(ref.ref, "action.concurrency")

        ref = PolicyTypeReference.from_string_reference("action.concurrency.targeted")
        self.assertEqual(ref.resource_type, "action")
        self.assertEqual(ref.name, "concurrency.targeted")
        self.assertEqual(ref.ref, "action.concurrency.targeted")

        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.from_string_reference, ".test"
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.from_string_reference, ""
        )
        self.assertRaises(
            InvalidReferenceError, PolicyTypeReference.from_string_reference, None
        )


class PolicyTypeTest(DbModelTestCase):
    access_type = PolicyType

    @staticmethod
    def _create_instance():
        parameters = {"threshold": {"type": "integer", "required": True}}

        instance = PolicyTypeDB(
            name="concurrency",
            description="TBD",
            enabled=None,
            ref=None,
            resource_type="action",
            module="st2action.policies.concurrency",
            parameters=parameters,
        )

        return instance

    def test_crud(self):
        instance = self._create_instance()

        defaults = {"ref": "action.concurrency", "enabled": True}

        updates = {"description": "Limits the concurrent executions for the action."}

        self._assert_crud(instance, defaults=defaults, updates=updates)

    def test_unique_key(self):
        instance = self._create_instance()
        self._assert_unique_key_constraint(instance)


class PolicyTest(DbModelTestCase):
    access_type = Policy

    @staticmethod
    def _create_instance():
        instance = PolicyDB(
            pack=None,
            name="local.concurrency",
            description="TBD",
            enabled=None,
            ref=None,
            resource_ref="core.local",
            policy_type="action.concurrency",
            parameters={"threshold": 25},
        )

        return instance

    def test_crud(self):
        instance = self._create_instance()

        defaults = {
            "pack": pack_constants.DEFAULT_PACK_NAME,
            "ref": "%s.local.concurrency" % pack_constants.DEFAULT_PACK_NAME,
            "enabled": True,
        }

        updates = {
            "description": 'Limits the concurrent executions for the action "core.local".'
        }

        self._assert_crud(instance, defaults=defaults, updates=updates)

    def test_ref(self):
        instance = self._create_instance()
        ref = instance.get_reference()
        self.assertIsNotNone(ref)
        self.assertEqual(ref.pack, instance.pack)
        self.assertEqual(ref.name, instance.name)
        self.assertEqual(ref.ref, instance.pack + "." + instance.name)
        self.assertEqual(ref.ref, instance.ref)

    def test_unique_key(self):
        instance = self._create_instance()
        self._assert_unique_key_constraint(instance)
