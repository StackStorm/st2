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

import os

import unittest2

import yaml

from yaml import SafeLoader, FullLoader

try:
    from yaml import CSafeLoader
except ImportError:
    CSafeLoader = None

from mock import Mock

from st2common.content.loader import ContentPackLoader
from st2common.content.loader import LOG
from st2common.constants.meta import yaml_safe_load

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
RESOURCES_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "../resources"))


class ContentLoaderTest(unittest2.TestCase):
    def test_get_sensors(self):
        packs_base_path = os.path.join(RESOURCES_DIR, "packs/")
        loader = ContentPackLoader()
        pack_sensors = loader.get_content(
            base_dirs=[packs_base_path], content_type="sensors"
        )
        self.assertIsNotNone(pack_sensors.get("pack1", None))

    def test_get_sensors_pack_missing_sensors(self):
        loader = ContentPackLoader()
        fail_pack_path = os.path.join(RESOURCES_DIR, "packs/pack2")
        self.assertTrue(os.path.exists(fail_pack_path))
        self.assertEqual(loader._get_sensors(fail_pack_path), None)

    def test_invalid_content_type(self):
        packs_base_path = os.path.join(RESOURCES_DIR, "packs/")
        loader = ContentPackLoader()
        self.assertRaises(
            ValueError,
            loader.get_content,
            base_dirs=[packs_base_path],
            content_type="stuff",
        )

    def test_get_content_multiple_directories(self):
        packs_base_path_1 = os.path.join(RESOURCES_DIR, "packs/")
        packs_base_path_2 = os.path.join(RESOURCES_DIR, "packs2/")
        base_dirs = [packs_base_path_1, packs_base_path_2]

        LOG.warning = Mock()

        loader = ContentPackLoader()
        sensors = loader.get_content(base_dirs=base_dirs, content_type="sensors")
        self.assertIn("pack1", sensors)  # from packs/
        self.assertIn("pack3", sensors)  # from packs2/

        # Assert that a warning is emitted when a duplicated pack is found
        expected_msg = (
            'Pack "pack1" already found in '
            '"%s/packs/", ignoring content from '
            '"%s/packs2/"' % (RESOURCES_DIR, RESOURCES_DIR)
        )
        LOG.warning.assert_called_once_with(expected_msg)

    def test_get_content_from_pack_success(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, "packs/pack1")

        sensors = loader.get_content_from_pack(
            pack_dir=pack_path, content_type="sensors"
        )
        self.assertTrue(sensors.endswith("packs/pack1/sensors"))

    def test_get_content_from_pack_directory_doesnt_exist(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, "packs/pack100")

        message_regex = "Directory .*? doesn't exist"
        self.assertRaisesRegexp(
            ValueError,
            message_regex,
            loader.get_content_from_pack,
            pack_dir=pack_path,
            content_type="sensors",
        )

    def test_get_content_from_pack_no_sensors(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(RESOURCES_DIR, "packs/pack2")

        result = loader.get_content_from_pack(
            pack_dir=pack_path, content_type="sensors"
        )
        self.assertEqual(result, None)


class YamlLoaderTestCase(unittest2.TestCase):
    def test_yaml_safe_load(self):
        # Verify C version of yaml loader indeed doesn't load non-safe data
        dumped = yaml.dump(Foo)
        self.assertTrue("!!python" in dumped)

        # Regular full load should work, but safe wrapper should fail
        result = yaml.load(dumped, Loader=FullLoader)
        self.assertTrue(result)

        self.assertRaisesRegexp(
            yaml.constructor.ConstructorError,
            "could not determine a constructor",
            yaml_safe_load,
            dumped,
        )

        self.assertRaisesRegexp(
            yaml.constructor.ConstructorError,
            "could not determine a constructor",
            yaml.load,
            dumped,
            Loader=SafeLoader,
        )

        if CSafeLoader:
            self.assertRaisesRegexp(
                yaml.constructor.ConstructorError,
                "could not determine a constructor",
                yaml.load,
                dumped,
                Loader=CSafeLoader,
            )


class Foo(object):
    a = "1"
    b = "c"
