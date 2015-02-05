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
from mock import Mock

from st2common.content.loader import ContentPackLoader
from st2common.content.loader import LOG

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, '../resources'))


class ContentLoaderTest(unittest2.TestCase):
    def test_get_sensors(self):
        packs_base_path = os.path.join(RESOURCES_DIR, 'packs/')
        loader = ContentPackLoader()
        pack_sensors = loader.get_content(base_dirs=[packs_base_path], content_type='sensors')
        self.assertTrue(pack_sensors.get('pack1', None) is not None)

    def test_get_sensors_pack_missing_sensors(self):
        loader = ContentPackLoader()
        fail_pack_path = os.path.join(RESOURCES_DIR, 'packs/pack2')
        self.assertTrue(os.path.exists(fail_pack_path))
        self.assertRaises(ValueError, loader._get_sensors, fail_pack_path)

    def test_invalid_content_type(self):
        packs_base_path = os.path.join(RESOURCES_DIR, 'packs/')
        loader = ContentPackLoader()
        self.assertRaises(ValueError, loader.get_content, base_dirs=[packs_base_path],
                          content_type='stuff')

    def test_get_content_multiple_directories(self):
        packs_base_path_1 = os.path.join(RESOURCES_DIR, 'packs/')
        packs_base_path_2 = os.path.join(RESOURCES_DIR, 'packs2/')
        base_dirs = [packs_base_path_1, packs_base_path_2]

        LOG.warning = Mock()

        loader = ContentPackLoader()
        sensors = loader.get_content(base_dirs=base_dirs, content_type='sensors')
        self.assertTrue('pack1' in sensors)  # from packs/
        self.assertTrue('pack3' in sensors)  # from packs2/

        # Assert that a warning is emitted when a duplicated pack is found
        expected_msg = ('Pack "pack1" already found in '
                        '"%s/packs/", ignoring content from '
                        '"%s/packs2/"' % (RESOURCES_DIR, RESOURCES_DIR))
        LOG.warning.assert_called_once_with(expected_msg)

    def test_get_content_from_pack_success(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, 'packs/pack1')

        sensors = loader.get_content_from_pack(pack_dir=pack_path, content_type='sensors')
        self.assertTrue(sensors.endswith('packs/pack1/sensors'))

    def test_get_content_from_pack_directory_doesnt_exist(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, 'packs/pack100')

        message_regex = 'Directory .*? doesn\'t exist'
        self.assertRaisesRegexp(ValueError, message_regex, loader.get_content_from_pack,
                                pack_dir=pack_path, content_type='sensors')

    def test_get_content_from_pack_no_sensors(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, 'packs/pack2')

        message_regex = 'No sensors found'
        self.assertRaisesRegexp(ValueError, message_regex, loader.get_content_from_pack,
                                pack_dir=pack_path, content_type='sensors')
