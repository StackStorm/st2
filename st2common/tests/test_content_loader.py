import os

import unittest2

from st2common.content.loader import ContentPackLoader


class ContentLoaderTest(unittest2.TestCase):

    def test_get_sensors(self):
        packs_base_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'resources/packs/')
        loader = ContentPackLoader()
        pack_sensors = loader.get_content(base_dir=packs_base_path, content_type='sensors')
        self.assertTrue(pack_sensors.get('pack1', None) is not None)

    def test_get_sensors_pack_missing_sensors(self):
        loader = ContentPackLoader()
        fail_pack_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'resources/packs/pack2')
        self.assertTrue(os.path.exists(fail_pack_path))
        try:
            loader._get_sensors(fail_pack_path)
            self.fail('Empty packs must throw exception.')
        except:
            pass

    def test_invalid_content_type(self):
        packs_base_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'resources/packs/')
        loader = ContentPackLoader()
        try:
            loader.get_content(base_dir=packs_base_path, content_type='stuff')
            self.fail('Asking for invalid content should have thrown.')
        except:
            pass
