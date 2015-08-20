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

from oslo_config import cfg
import unittest2

from st2common.constants.action import LIBS_DIR as ACTION_LIBS_DIR
from st2actions.container.service import RunnerContainerService
from st2tests import config as tests_config


class RunnerContainerServiceTest(unittest2.TestCase):
    @classmethod
    def setUpClass(cls):
        tests_config.parse_args()

    def test_get_pack_base_path(self):
        orig_path = cfg.CONF.content.system_packs_base_path
        cfg.CONF.content.system_packs_base_path = '/tests/packs'

        names = [
            'test_pack_1',
            'test_pack_2',
            'ma_pack'
        ]

        for name in names:
            actual = RunnerContainerService().get_pack_base_path(pack_name=name)
            expected = os.path.join(cfg.CONF.content.system_packs_base_path,
                                    name)
            self.assertEqual(actual, expected)

        cfg.CONF.content.system_packs_base_path = orig_path

    def test_get_entry_point_absolute_path(self):
        service = RunnerContainerService()
        orig_path = cfg.CONF.content.system_packs_base_path
        cfg.CONF.content.system_packs_base_path = '/tests/packs'
        acutal_path = service.get_entry_point_abs_path(pack='foo',
                                                       entry_point='/tests/packs/foo/bar.py')
        self.assertEqual(acutal_path, '/tests/packs/foo/bar.py', 'Entry point path doesn\'t match.')
        cfg.CONF.content.system_packs_base_path = orig_path

    def test_get_entry_point_absolute_path_empty(self):
        service = RunnerContainerService()
        orig_path = cfg.CONF.content.system_packs_base_path
        cfg.CONF.content.system_packs_base_path = '/tests/packs'
        acutal_path = service.get_entry_point_abs_path(pack='foo', entry_point=None)
        self.assertEqual(acutal_path, None, 'Entry point path doesn\'t match.')
        acutal_path = service.get_entry_point_abs_path(pack='foo', entry_point='')
        self.assertEqual(acutal_path, None, 'Entry point path doesn\'t match.')
        cfg.CONF.content.system_packs_base_path = orig_path

    def test_get_entry_point_relative_path(self):
        service = RunnerContainerService()
        orig_path = cfg.CONF.content.system_packs_base_path
        cfg.CONF.content.system_packs_base_path = '/tests/packs'
        acutal_path = service.get_entry_point_abs_path(pack='foo', entry_point='foo/bar.py')
        expected_path = os.path.join(cfg.CONF.content.system_packs_base_path, 'foo', 'actions',
                                     'foo/bar.py')
        self.assertEqual(acutal_path, expected_path, 'Entry point path doesn\'t match.')
        cfg.CONF.content.system_packs_base_path = orig_path

    def test_get_action_libs_abs_path(self):
        service = RunnerContainerService()
        orig_path = cfg.CONF.content.system_packs_base_path
        cfg.CONF.content.system_packs_base_path = '/tests/packs'

        # entry point relative.
        acutal_path = service.get_action_libs_abs_path(pack='foo', entry_point='foo/bar.py')
        expected_path = os.path.join(cfg.CONF.content.system_packs_base_path, 'foo', 'actions',
                                     os.path.join('foo', ACTION_LIBS_DIR))
        self.assertEqual(acutal_path, expected_path, 'Action libs path doesn\'t match.')

        # entry point absolute.
        acutal_path = service.get_action_libs_abs_path(pack='foo',
                                                       entry_point='/tests/packs/foo/tmp/foo.py')
        expected_path = os.path.join('/tests/packs/foo/tmp', ACTION_LIBS_DIR)
        self.assertEqual(acutal_path, expected_path, 'Action libs path doesn\'t match.')
        cfg.CONF.content.system_packs_base_path = orig_path
