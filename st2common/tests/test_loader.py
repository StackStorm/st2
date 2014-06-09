import abc
import copy
import os
import six
import shutil
import sys
import unittest2

import st2common.util.loader as plugin_loader


PLUGIN_FOLDER = 'loadableplugin'
SRC_RELATIVE = 'resources/{}'.format(PLUGIN_FOLDER)
SRC_ROOT = '{}/{}'.format(os.path.abspath(os.path.dirname(__file__)),
                          SRC_RELATIVE)

DST_ROOT = '/tmp/{}'.format(PLUGIN_FOLDER)


class LoaderTest(unittest2.TestCase):
    sys_path = 0

    @six.add_metaclass(abc.ABCMeta)
    class DummyPlugin(object):
        """
        Base class that test plugins should implement
        """

        @abc.abstractmethod
        def do_work(self):
            pass

    @classmethod
    def setUpClass(cls):
        if os.path.exists(DST_ROOT):
            LoaderTest.tearDownClass()
        shutil.copytree(SRC_ROOT, DST_ROOT)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(DST_ROOT)

    # setUp and tearDown are used to reset the python path for each test to
    # prevent a test from affecting another.
    def setUp(self):
        LoaderTest.sys_path = copy.copy(sys.path)

    def tearDown(self):
        sys.path = LoaderTest.sys_path

    def test_module_load_from_file(self):
        plugin_path = '{}/{}'.format(DST_ROOT, 'plugin/standaloneplugin.py')
        plugin_instances = plugin_loader.register_plugin(
            LoaderTest.DummyPlugin, plugin_path)
        # Even though there are two classes in that file, only one
        # matches the specs of DummyPlugin class.
        # XXX: ABC does not validate that a class that is being
        # registered has the methods defined in base class. Fix
        # this when manual validation is added.
        self.assertEquals(2, len(plugin_instances))
        # Validate sys.path now contains the plugin directory.
        self.assertTrue('{}/{}'.format(DST_ROOT, 'plugin') in sys.path)
        # Validate the individual plugins
        for plugin_instance in plugin_instances:
            try:
                ret_val = plugin_instance.do_work()
                self.assertIsNotNone(ret_val, 'Should be non-null.')
            except:
                # XXX: Classes that don't implement do_work()
                # will throw exceptions
                pass

    def test_module_load_from_file_fail(self):
        try:
            plugin_path = '{}/{}'.format(DST_ROOT, 'plugin/sampleplugin.py')
            plugin_loader.register_plugin(LoaderTest.DummyPlugin, plugin_path)
            self.assertTrue(False, 'Import error is expected.')
        except ImportError:
            self.assertTrue(True)

    def test_syspath_unchanged_load_multiple_plugins(self):
        plugin_1_path = '{}/{}'.format(DST_ROOT, 'plugin/sampleplugin.py')
        try:
            plugin_loader.register_plugin(
                LoaderTest.DummyPlugin, plugin_1_path)
        except ImportError:
            pass
        old_sys_path = copy.copy(sys.path)

        plugin_2_path = '{}/{}'.format(DST_ROOT, 'plugin/sampleplugin2.py')
        try:
            plugin_loader.register_plugin(
                LoaderTest.DummyPlugin, plugin_2_path)
        except ImportError:
            pass
        self.assertEquals(old_sys_path, sys.path, 'Should be equal.')
