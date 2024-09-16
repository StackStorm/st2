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

from oslo_config import cfg
import os

import unittest

import yaml

from yaml import SafeLoader, FullLoader

try:
    from yaml import CSafeLoader
except ImportError:
    CSafeLoader = None

from mock import Mock

from st2common.content.loader import ContentPackLoader
from st2common.content.loader import OverrideLoader
from st2common.content.loader import LOG
from st2common.constants.meta import yaml_safe_load
from st2tests import config

from tests.resources.packs.fixture import PACKS_BASE_PATH as PACKS_BASE_PATH_1
from tests.resources.packs2.fixture import PACKS_BASE_PATH as PACKS_BASE_PATH_2
from tests.resources.packs3.fixture import PACKS_BASE_PATH as PACKS_BASE_PATH_3


class ContentLoaderTest(unittest.TestCase):
    def test_get_sensors(self):
        loader = ContentPackLoader()
        pack_sensors = loader.get_content(
            base_dirs=[PACKS_BASE_PATH_1], content_type="sensors"
        )
        self.assertIsNotNone(pack_sensors.get("pack1", None))

    def test_get_sensors_pack_missing_sensors(self):
        loader = ContentPackLoader()
        fail_pack_path = os.path.join(PACKS_BASE_PATH_1, "pack2")
        self.assertTrue(os.path.exists(fail_pack_path))
        self.assertEqual(loader._get_sensors(fail_pack_path), None)

    def test_invalid_content_type(self):
        loader = ContentPackLoader()
        self.assertRaises(
            ValueError,
            loader.get_content,
            base_dirs=[PACKS_BASE_PATH_1],
            content_type="stuff",
        )

    def test_get_content_multiple_directories(self):
        base_dirs = [PACKS_BASE_PATH_1, PACKS_BASE_PATH_2]

        LOG.warning = Mock()

        loader = ContentPackLoader()
        sensors = loader.get_content(base_dirs=base_dirs, content_type="sensors")
        self.assertIn("pack1", sensors)  # from packs/
        self.assertIn("pack3", sensors)  # from packs2/

        # Assert that a warning is emitted when a duplicated pack is found
        expected_msg = (
            'Pack "pack1" already found in '
            f'"{PACKS_BASE_PATH_1}", ignoring content from '
            f'"{PACKS_BASE_PATH_2}"'
        )
        LOG.warning.assert_called_once_with(expected_msg)

    def test_get_content_from_pack_success(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(PACKS_BASE_PATH_1, "pack1")

        sensors = loader.get_content_from_pack(
            pack_dir=pack_path, content_type="sensors"
        )
        self.assertTrue(sensors.endswith("packs/pack1/sensors"))

    def test_get_content_from_pack_directory_doesnt_exist(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(PACKS_BASE_PATH_1, "pack100")

        message_regex = "Directory .*? doesn't exist"
        self.assertRaisesRegex(
            ValueError,
            message_regex,
            loader.get_content_from_pack,
            pack_dir=pack_path,
            content_type="sensors",
        )

    def test_get_content_from_pack_no_sensors(self):
        loader = ContentPackLoader()
        pack_path = os.path.join(PACKS_BASE_PATH_1, "pack2")

        result = loader.get_content_from_pack(
            pack_dir=pack_path, content_type="sensors"
        )
        self.assertEqual(result, None)

    def test_get_override_action_from_default(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action1", "enabled": True}
        self.assertTrue(loader.override("overpack1", "actions", content))
        self.assertFalse(content["enabled"])
        content = {"name": "action1", "enabled": False}
        self.assertFalse(loader.override("overpack1", "actions", content))
        self.assertFalse(content["enabled"])

    def test_get_override_action_from_exception(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action2", "enabled": True}
        self.assertFalse(loader.override("overpack1", "actions", content))
        self.assertTrue(content["enabled"])
        content = {"name": "action2", "enabled": False}
        self.assertTrue(loader.override("overpack1", "actions", content))
        self.assertTrue(content["enabled"])

    def test_get_override_action_from_default_no_exceptions(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action1", "enabled": True}
        self.assertTrue(loader.override("overpack4", "actions", content))
        self.assertFalse(content["enabled"])
        content = {"name": "action2", "enabled": True}
        self.assertTrue(loader.override("overpack4", "actions", content))
        self.assertFalse(content["enabled"])

    def test_get_override_action_from_global_default_no_exceptions(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"class_name": "sensor1", "enabled": True}
        self.assertTrue(loader.override("overpack1", "sensors", content))
        self.assertFalse(content["enabled"])

    def test_get_override_action_from_global_overridden_by_pack(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"class_name": "sensor1", "enabled": True}
        self.assertFalse(loader.override("overpack2", "sensors", content))
        self.assertTrue(content["enabled"])

    def test_get_override_action_from_global_overridden_by_pack_exception(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"class_name": "sensor1", "enabled": True}
        self.assertFalse(loader.override("overpack3", "sensors", content))
        self.assertTrue(content["enabled"])

    def test_get_override_invalid_type(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action2", "enabled": True}
        self.assertRaises(
            ValueError,
            loader.override,
            pack_name="overpack1",
            resource_type="wrongtype",
            content=content,
        )

    def test_get_override_invalid_default_key(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action1", "enabled": True}
        self.assertRaises(
            ValueError,
            loader.override,
            pack_name="overpack2",
            resource_type="actions",
            content=content,
        )

    def test_get_override_invalid_exceptions_key(self):
        config.parse_args()
        cfg.CONF.set_override(
            name="base_path", override=PACKS_BASE_PATH_3, group="system"
        )
        loader = OverrideLoader()
        content = {"name": "action1", "enabled": True}
        loader.override("overpack1", "actions", content)
        content = {"name": "action2", "enabled": True}
        self.assertRaises(
            ValueError,
            loader.override,
            pack_name="overpack3",
            resource_type="actions",
            content=content,
        )


class YamlLoaderTestCase(unittest.TestCase):
    def test_yaml_safe_load(self):
        # Verify C version of yaml loader indeed doesn't load non-safe data
        dumped = yaml.dump(Foo)
        self.assertTrue("!!python" in dumped)

        # Regular full load should work, but safe wrapper should fail
        result = yaml.load(dumped, Loader=FullLoader)
        self.assertTrue(result)

        self.assertRaisesRegex(
            yaml.constructor.ConstructorError,
            "could not determine a constructor",
            yaml_safe_load,
            dumped,
        )

        self.assertRaisesRegex(
            yaml.constructor.ConstructorError,
            "could not determine a constructor",
            yaml.load,
            dumped,
            Loader=SafeLoader,
        )

        if CSafeLoader:
            self.assertRaisesRegex(
                yaml.constructor.ConstructorError,
                "could not determine a constructor",
                yaml.load,
                dumped,
                Loader=CSafeLoader,
            )


class Foo(object):
    a = "1"
    b = "c"
