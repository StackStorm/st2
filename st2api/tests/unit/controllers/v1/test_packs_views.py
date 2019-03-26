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

import mock

from six.moves import http_client
import st2common.bootstrap.actionsregistrar as actions_registrar
from st2common.persistence.pack import Pack
from st2tests.api import FunctionalTest


@mock.patch('st2common.bootstrap.base.REGISTERED_PACKS_CACHE', {})
class PacksViewsControllerTestCase(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(PacksViewsControllerTestCase, cls).setUpClass()

        # Register local action and pack fixtures
        actions_registrar.register_actions(use_pack_cache=False)

    def test_get_pack_files_success(self):
        resp = self.app.get('/v1/packs/views/files/dummy_pack_1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(len(resp.json) > 1)
        item = [_item for _item in resp.json if _item['file_path'] == 'pack.yaml'][0]
        self.assertEqual(item['file_path'], 'pack.yaml')
        item = [_item for _item in resp.json if _item['file_path'] == 'actions/my_action.py'][0]
        self.assertEqual(item['file_path'], 'actions/my_action.py')

    def test_get_pack_files_pack_doesnt_exist(self):
        resp = self.app.get('/v1/packs/views/files/doesntexist', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_get_pack_files_binary_files_are_excluded(self):
        binary_files = [
            'icon.png',
            'etc/permissions.png',
            'etc/travisci.png',
            'etc/generate_new_token.png'
        ]

        pack_db = Pack.get_by_ref('dummy_pack_1')

        all_files_count = len(pack_db.files)
        non_binary_files_count = all_files_count - len(binary_files)

        resp = self.app.get('/v1/packs/views/files/dummy_pack_1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), non_binary_files_count)

        for file_path in binary_files:
            self.assertTrue(file_path in pack_db.files)

        # But not in files controller response
        for file_path in binary_files:
            item = [item for item in resp.json if item['file_path'] == file_path]
            self.assertFalse(item)

    def test_get_pack_file_success(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(b'name : dummy_pack_1' in resp.body)

    def test_get_pack_file_pack_doesnt_exist(self):
        resp = self.app.get('/v1/packs/views/files/doesntexist/pack.yaml', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    @mock.patch('st2api.controllers.v1.pack_views.MAX_FILE_SIZE', 1)
    def test_pack_file_file_larger_then_maximum_size(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.BAD_REQUEST)
        self.assertTrue('File pack.yaml exceeds maximum allowed file size' in resp)

    def test_headers_get_pack_file(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(b'name : dummy_pack_1' in resp.body)
        self.assertIsNotNone(resp.headers['ETag'])
        self.assertIsNotNone(resp.headers['Last-Modified'])

    def test_no_change_get_pack_file(self):
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(b'name : dummy_pack_1' in resp.body)

        # Confirm NOT_MODIFIED
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml',
                            headers={'If-None-Match': resp.headers['ETag']})
        self.assertEqual(resp.status_code, http_client.NOT_MODIFIED)

        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml',
                            headers={'If-Modified-Since': resp.headers['Last-Modified']})
        self.assertEqual(resp.status_code, http_client.NOT_MODIFIED)

        # Confirm value is returned if header do not match
        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml',
                            headers={'If-None-Match': 'ETAG'})
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue(b'name : dummy_pack_1' in resp.body)

        resp = self.app.get('/v1/packs/views/file/dummy_pack_1/pack.yaml',
                            headers={'If-Modified-Since': 'Last-Modified'})
        self.assertEqual(resp.status_code, http_client.OK)
        self.assertTrue(b'name : dummy_pack_1' in resp.body)

    def test_get_pack_files_and_pack_file_ref_doesnt_equal_pack_name(self):
        # Ref is not equal to the name, controller should still work
        resp = self.app.get('/v1/packs/views/files/dummy_pack_16')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['file_path'], 'pack.yaml')

        resp = self.app.get('/v1/packs/views/file/dummy_pack_16/pack.yaml')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertTrue(b'ref: dummy_pack_16' in resp.body)
