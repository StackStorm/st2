import unittest2

from st2common.models.system.common import ResourceReference


class ResourceReferenceTestCase(unittest2.TestCase):
    def test_resource_reference(self):
        value = 'pack1.name1'
        ref = ResourceReference.from_string_reference(ref=value)

        self.assertEqual(ref.pack, 'pack1')
        self.assertEqual(ref.name, 'name1')
        self.assertEqual(ref.ref, value)

        ref = ResourceReference(pack='pack1', name='name1')
        self.assertEqual(ref.ref, 'pack1.name1')

        ref = ResourceReference(pack='pack1', name='name1.name2')
        self.assertEqual(ref.ref, 'pack1.name1.name2')

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
