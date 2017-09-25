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

import imp
import os
import mock
import unittest2

from oslo_config import cfg

from st2common import config
from st2common.util import loader


CURRENT_DIR = os.path.dirname(__file__)
ST2CONTENT_DIR = os.path.join(CURRENT_DIR, '../fixtures')
MOCK_RUNNER_NAME = 'mock_runner'
MOCK_RUNNER_PATH = '{0}/{1}/{1}.py'.format(ST2CONTENT_DIR, MOCK_RUNNER_NAME)
MOCK_RUNNER_MODULE = imp.load_source(MOCK_RUNNER_NAME, MOCK_RUNNER_PATH)
MOCK_QUERIER_PATH = '{0}/{1}/query/{1}.py'.format(ST2CONTENT_DIR, MOCK_RUNNER_NAME)
MOCK_QUERIER_MODULE = imp.load_source(MOCK_RUNNER_NAME, MOCK_QUERIER_PATH)
MOCK_CALLBACK_PATH = '{0}/{1}/callback/{1}.py'.format(ST2CONTENT_DIR, MOCK_RUNNER_NAME)
MOCK_CALLBACK_MODULE = imp.load_source(MOCK_RUNNER_NAME, MOCK_CALLBACK_PATH)


class PluginLoaderTestCase(unittest2.TestCase):

    @classmethod
    def setUpClass(cls):
        super(PluginLoaderTestCase, cls).setUpClass()

        # Check to see if configs are already registered.
        # The register_opts is needed when running tests individually.
        if 'system' not in cfg.CONF:
            config.register_opts()

    def setUp(self):
        super(PluginLoaderTestCase, self).setUp()
        loader.RUNNER_MODULES_CACHE = {}
        loader.QUERIER_MODULES_CACHE = {}
        loader.CALLBACK_MODULES_CACHE = {}

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_RUNNER_MODULE)
    )
    def test_register_runner(self):
        runner = loader.register_runner(MOCK_RUNNER_NAME)

        self.assertIsNotNone(runner)
        self.assertEqual(MOCK_RUNNER_NAME, runner.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.RUNNER_MODULES_CACHE)
        self.assertEqual(runner, loader.RUNNER_MODULES_CACHE[MOCK_RUNNER_NAME])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_RUNNER_MODULE)
    )
    def test_register_runner_again(self):
        runner1 = loader.register_runner(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertIsNotNone(runner1)
        self.assertEqual(MOCK_RUNNER_NAME, runner1.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.RUNNER_MODULES_CACHE)
        self.assertEqual(runner1, loader.RUNNER_MODULES_CACHE[MOCK_RUNNER_NAME])

        runner2 = loader.register_runner(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertEqual(runner1, runner2)
        self.assertIsNotNone(runner2)
        self.assertEqual(MOCK_RUNNER_NAME, runner2.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.RUNNER_MODULES_CACHE)
        self.assertEqual(runner2, loader.RUNNER_MODULES_CACHE[MOCK_RUNNER_NAME])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_QUERIER_MODULE)
    )
    def test_register_query_module(self):
        querier = loader.register_query_module(MOCK_RUNNER_NAME)

        self.assertIsNotNone(querier)
        self.assertEqual(MOCK_RUNNER_NAME, querier.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.QUERIER_MODULES_CACHE)
        self.assertEqual(querier, loader.QUERIER_MODULES_CACHE[MOCK_RUNNER_NAME])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_QUERIER_MODULE)
    )
    def test_register_query_module_again(self):
        querier1 = loader.register_query_module(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertIsNotNone(querier1)
        self.assertEqual(MOCK_RUNNER_NAME, querier1.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.QUERIER_MODULES_CACHE)
        self.assertEqual(querier1, loader.QUERIER_MODULES_CACHE[MOCK_RUNNER_NAME])

        querier2 = loader.register_query_module(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertEqual(querier1, querier2)
        self.assertIsNotNone(querier2)
        self.assertEqual(MOCK_RUNNER_NAME, querier2.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.QUERIER_MODULES_CACHE)
        self.assertEqual(querier2, loader.QUERIER_MODULES_CACHE[MOCK_RUNNER_NAME])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_CALLBACK_MODULE)
    )
    def test_register_callback_module(self):
        callback_module = loader.register_callback_module(MOCK_RUNNER_NAME)

        self.assertIsNotNone(callback_module)
        self.assertEqual(MOCK_RUNNER_NAME, callback_module.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.CALLBACK_MODULES_CACHE)
        self.assertEqual(callback_module, loader.CALLBACK_MODULES_CACHE[MOCK_RUNNER_NAME])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_CALLBACK_MODULE)
    )
    def test_register_callback_module_again(self):
        callback_module1 = loader.register_callback_module(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertIsNotNone(callback_module1)
        self.assertEqual(MOCK_RUNNER_NAME, callback_module1.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.CALLBACK_MODULES_CACHE)
        self.assertEqual(callback_module1, loader.CALLBACK_MODULES_CACHE[MOCK_RUNNER_NAME])

        callback_module2 = loader.register_callback_module(MOCK_RUNNER_NAME)

        self.assertEqual(1, imp.load_source.call_count)
        self.assertEqual(callback_module1, callback_module2)
        self.assertIsNotNone(callback_module2)
        self.assertEqual(MOCK_RUNNER_NAME, callback_module2.__name__)
        self.assertIn(MOCK_RUNNER_NAME, loader.CALLBACK_MODULES_CACHE)
        self.assertEqual(callback_module2, loader.CALLBACK_MODULES_CACHE[MOCK_RUNNER_NAME])
