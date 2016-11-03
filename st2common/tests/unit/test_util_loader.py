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
MOCK_RUNNER_PATH = os.path.join('%s/mock_runner/mock_runner.py' % ST2CONTENT_DIR)
MOCK_RUNNER_MODULE = imp.load_source('mock_runner', MOCK_RUNNER_PATH)
MOCK_QUERIER_PATH = os.path.join('%s/mock_runner/query/mock_runner.py' % ST2CONTENT_DIR)
MOCK_QUERIER_MODULE = imp.load_source('mock_runner', MOCK_QUERIER_PATH)


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
        loader.RUNNER_MODULES = {}
        loader.QUERIER_MODULES = {}

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_RUNNER_MODULE)
    )
    def test_register_runner(self):
        runner = loader.register_runner('mock_runner')

        self.assertIsNotNone(runner)
        self.assertEqual('mock_runner', runner.__name__)
        self.assertIn('mock_runner', loader.RUNNER_MODULES)
        self.assertEqual(runner, loader.RUNNER_MODULES['mock_runner'])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_RUNNER_MODULE)
    )
    def test_register_runner_again(self):
        runner1 = loader.register_runner('mock_runner')

        self.assertEqual(1, imp.load_source.call_count)
        self.assertIsNotNone(runner1)
        self.assertEqual('mock_runner', runner1.__name__)
        self.assertIn('mock_runner', loader.RUNNER_MODULES)
        self.assertEqual(runner1, loader.RUNNER_MODULES['mock_runner'])

        runner2 = loader.register_runner('mock_runner')

        self.assertEqual(1, imp.load_source.call_count)
        self.assertEqual(runner1, runner2)
        self.assertIsNotNone(runner2)
        self.assertEqual('mock_runner', runner2.__name__)
        self.assertIn('mock_runner', loader.RUNNER_MODULES)
        self.assertEqual(runner2, loader.RUNNER_MODULES['mock_runner'])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_QUERIER_MODULE)
    )
    def test_register_query_module(self):
        querier = loader.register_query_module('mock_runner')

        self.assertIsNotNone(querier)
        self.assertEqual('mock_runner', querier.__name__)
        self.assertIn('mock_runner', loader.QUERIER_MODULES)
        self.assertEqual(querier, loader.QUERIER_MODULES['mock_runner'])

    @mock.patch.object(
        imp,
        'load_source',
        mock.MagicMock(return_value=MOCK_QUERIER_MODULE)
    )
    def test_register_query_module_again(self):
        querier1 = loader.register_query_module('mock_runner')

        self.assertEqual(1, imp.load_source.call_count)
        self.assertIsNotNone(querier1)
        self.assertEqual('mock_runner', querier1.__name__)
        self.assertIn('mock_runner', loader.QUERIER_MODULES)
        self.assertEqual(querier1, loader.QUERIER_MODULES['mock_runner'])

        querier2 = loader.register_query_module('mock_runner')

        self.assertEqual(1, imp.load_source.call_count)
        self.assertEqual(querier1, querier2)
        self.assertIsNotNone(querier2)
        self.assertEqual('mock_runner', querier2.__name__)
        self.assertIn('mock_runner', loader.QUERIER_MODULES)
        self.assertEqual(querier2, loader.QUERIER_MODULES['mock_runner'])
