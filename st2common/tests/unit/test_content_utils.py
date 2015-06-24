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

import unittest2
from oslo_config import cfg

from st2common.content.utils import get_packs_base_paths, get_aliases_base_paths
from st2tests import config as tests_config


class ContentUtilsTestCase(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_get_pack_base_paths(self):
        cfg.CONF.content.system_packs_base_path = ''
        cfg.CONF.content.packs_base_paths = '/opt/path1'
        result = get_packs_base_paths()
        self.assertEqual(result, ['/opt/path1'])

        # Multiple paths, no trailing colon
        cfg.CONF.content.packs_base_paths = '/opt/path1:/opt/path2'
        result = get_packs_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])

        # Multiple paths, trailing colon
        cfg.CONF.content.packs_base_paths = '/opt/path1:/opt/path2:'
        result = get_packs_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])

        # Multiple same paths
        cfg.CONF.content.packs_base_paths = '/opt/path1:/opt/path2:/opt/path1:/opt/path2'
        result = get_packs_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])

        # Assert system path is always first
        cfg.CONF.content.system_packs_base_path = '/opt/system'
        cfg.CONF.content.packs_base_paths = '/opt/path2:/opt/path1'
        result = get_packs_base_paths()
        self.assertEqual(result, ['/opt/system', '/opt/path2', '/opt/path1'])

    def test_get_aliases_base_paths(self):
        cfg.CONF.content.aliases_base_paths = '/opt/path1'
        result = get_aliases_base_paths()
        self.assertEqual(result, ['/opt/path1'])

        # Multiple paths, no trailing colon
        cfg.CONF.content.aliases_base_paths = '/opt/path1:/opt/path2'
        result = get_aliases_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])

        # Multiple paths, trailing colon
        cfg.CONF.content.aliases_base_paths = '/opt/path1:/opt/path2:'
        result = get_aliases_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])

        # Multiple same paths
        cfg.CONF.content.aliases_base_paths = '/opt/path1:/opt/path2:/opt/path1:/opt/path2'
        result = get_aliases_base_paths()
        self.assertEqual(result, ['/opt/path1', '/opt/path2'])
