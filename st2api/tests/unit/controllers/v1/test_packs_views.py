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

import httplib

import mock

import st2common.bootstrap.actionsregistrar as actions_registrar
from tests import FunctionalTest


class PacksViewsControllerTestCase(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(PacksViewsControllerTestCase, cls).setUpClass()

        # Register local action and pack fixtures
        actions_registrar.register_actions()

    def test_get_pack_files_success(self):
        resp = self.app.get('/v1/packs/views/files/dummy_pack_1')
        self.assertEqual(resp.status_int, httplib.OK)
        self.assertTrue(len(resp.json) > 1)
        item = [_item for _item in resp.json if _item['file_path'] == 'pack.yaml'][0]
        self.assertEqual(item['file_path'], 'pack.yaml')
        item = [_item for _item in resp.json if _item['file_path'] == 'actions/my_action.py'][0]
        self.assertEqual(item['file_path'], 'actions/my_action.py')

    def test_get_pack_files_pack_doesnt_exist(self):
        resp = self.app.get('/v1/packs/views/files/doesntexist', expect_errors=True)
        self.assertEqual(resp.status_int, httplib.NOT_FOUND)

    def test_get_pack_files_binary_files_are_excluded(self):
        resp = self.app.get('/v1/packs/views/files/dummy_pack_1')
        self.assertEqual(resp.status_int, httplib.OK)
        self.assertTrue(len(resp.json) > 1)
        icon_item = [item for item in resp.json if item['file_path'] == 'icon.png']
        self.assertFalse(icon_item)

    def test_get_pack_file_success(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml')
        self.assertEqual(resp.status_int, httplib.OK)
        self.assertTrue('name : dummy_pack_1' in resp.body)

    def test_get_pack_file_pack_doesnt_exist(self):
        resp = self.app.get('/v1/packs/views/files/doesntexist/pack.yaml', expect_errors=True)
        self.assertEqual(resp.status_int, httplib.NOT_FOUND)

    @mock.patch('st2api.controllers.v1.packviews.MAX_FILE_SIZE', 1)
    def test_pack_file_file_larger_then_maximum_size(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml', expect_errors=True)
        self.assertEqual(resp.status_int, httplib.BAD_REQUEST)
        self.assertTrue('File pack.yaml exceeds maximum allowed file size' in resp)
