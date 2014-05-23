import copy
import os
import shutil
import sys
import unittest2

import st2common.util.loader


PLUGIN_FOLDER = 'loadableplugin'
SRC_RELATIVE = 'resources/{}'.format(PLUGIN_FOLDER)
SRC_ROOT = '{}/{}'.format(os.path.abspath(os.path.dirname(__file__)),
                          SRC_RELATIVE)

DST_ROOT = '/tmp/{}'.format(PLUGIN_FOLDER)


class LoaderTest(unittest2.TestCase):
    sys_path = 0

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

    def test_module_load_from_path(self):
        factory = st2common.util.loader.get_plugin_factory_m(
            'plugin.sampleplugin', DST_ROOT)
        plugin_instance = factory()
        ret_val = plugin_instance.do_work()
        self.assertIsNotNone(ret_val, 'Should be non-null.')

    def test_module_load_from_file(self):
        factory = st2common.util.loader.get_plugin_factory_f(
            '{}/{}'.format(DST_ROOT, 'plugin/standaloneplugin.py'))
        plugin_instance = factory()
        ret_val = plugin_instance.do_work()
        self.assertIsNotNone(ret_val, 'Should be non-null.')

    def test_module_load_from_file_fail(self):
        try:
            st2common.util.loader.get_plugin_factory_f(
                '{}/{}'.format(DST_ROOT, 'plugin/sampleplugin.py'))
            self.assertTrue(False, 'Import error is expected.')
        except ImportError:
            self.assertTrue(True)

    def test_module_load_from_path_known_syspath(self):
        st2common.util.loader.get_plugin_factory_m('plugin.sampleplugin',
                                                   DST_ROOT)
        old_sys_path = copy.copy(sys.path)
        st2common.util.loader.get_plugin_factory_m('plugin.sampleplugin2',
                                                   DST_ROOT)
        self.assertEquals(old_sys_path, sys.path, 'Should be equal.')
