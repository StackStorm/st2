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
import abc
import copy
import os
import six
import sys
import unittest

import st2common.util.loader as plugin_loader


from tests.resources.loadableplugin.fixture import FIXTURE_PATH as SRC_ROOT


class LoaderTest(unittest.TestCase):
    sys_path = None

    @six.add_metaclass(abc.ABCMeta)
    class DummyPlugin(object):
        """
        Base class that test plugins should implement
        """

        @abc.abstractmethod
        def do_work(self):
            pass

    # setUp and tearDown are used to reset the python path for each test to
    # prevent a test from affecting another.
    def setUp(self):
        LoaderTest.sys_path = copy.copy(sys.path)

    def tearDown(self):
        sys.path = LoaderTest.sys_path

    def test_module_load_from_file(self):
        plugin_path = os.path.join(SRC_ROOT, "plugin/standaloneplugin.py")
        plugin_classes = plugin_loader.register_plugin(
            LoaderTest.DummyPlugin, plugin_path
        )
        # Even though there are two classes in that file, only one
        # matches the specs of DummyPlugin class.
        self.assertEqual(1, len(plugin_classes))
        # Validate sys.path now contains the plugin directory.
        self.assertIn(os.path.abspath(os.path.join(SRC_ROOT, "plugin")), sys.path)
        # Validate the individual plugins
        for plugin_class in plugin_classes:
            try:
                plugin_instance = plugin_class()
                ret_val = plugin_instance.do_work()
                self.assertIsNotNone(ret_val, "Should be non-null.")
            except:
                pass

    def test_module_load_from_file_fail(self):
        try:
            plugin_path = os.path.join(SRC_ROOT, "plugin/sampleplugin.py")
            plugin_loader.register_plugin(LoaderTest.DummyPlugin, plugin_path)
            self.assertTrue(False, "Import error is expected.")
        except ImportError:
            self.assertTrue(True)

    def test_syspath_unchanged_load_multiple_plugins(self):
        plugin_1_path = os.path.join(SRC_ROOT, "plugin/sampleplugin.py")
        try:
            plugin_loader.register_plugin(LoaderTest.DummyPlugin, plugin_1_path)
        except ImportError:
            pass
        old_sys_path = copy.copy(sys.path)

        plugin_2_path = os.path.join(SRC_ROOT, "plugin/sampleplugin2.py")
        try:
            plugin_loader.register_plugin(LoaderTest.DummyPlugin, plugin_2_path)
        except ImportError:
            pass
        self.assertEqual(old_sys_path, sys.path, "Should be equal.")

    def test_register_plugin_class_class_doesnt_exist(self):
        file_path = os.path.join(SRC_ROOT, "plugin/sampleplugin3.py")

        expected_msg = 'doesn\'t expose class named "SamplePluginNotExists"'
        self.assertRaisesRegex(
            Exception,
            expected_msg,
            plugin_loader.register_plugin_class,
            base_class=LoaderTest.DummyPlugin,
            file_path=file_path,
            class_name="SamplePluginNotExists",
        )

    def test_register_plugin_class_abstract_method_not_implemented(self):
        file_path = os.path.join(SRC_ROOT, "plugin/sampleplugin3.py")

        expected_msg = (
            'doesn\'t implement required "do_work" method from the base class'
        )
        self.assertRaisesRegex(
            plugin_loader.IncompatiblePluginException,
            expected_msg,
            plugin_loader.register_plugin_class,
            base_class=LoaderTest.DummyPlugin,
            file_path=file_path,
            class_name="SamplePlugin",
        )
