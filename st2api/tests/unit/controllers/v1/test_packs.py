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

from st2common.models.db.pack import PackDB
from st2common.persistence.pack import Pack
from tests import FunctionalTest


class PacksControllerTestCase(FunctionalTest):
    @classmethod
    def setUpClass(cls):
        super(PacksControllerTestCase, cls).setUpClass()

        cls.pack_db_1 = PackDB(name='pack1', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack1')
        cls.pack_db_2 = PackDB(name='pack2', description='foo', version='0.1.0', author='foo',
                               email='test@example.com', ref='pack2')
        Pack.add_or_update(cls.pack_db_1)
        Pack.add_or_update(cls.pack_db_2)

    def test_get_all(self):
        resp = self.app.get('/v1/packs')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/v1/actionalias did not return all aliases.')

    def test_get_one(self):
        # Get by id
        resp = self.app.get('/v1/packs/%s' % (self.pack_db_1.id))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['name'], self.pack_db_1.name)

        # Get by name
        resp = self.app.get('/v1/packs/%s' % (self.pack_db_1.ref))
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['ref'], self.pack_db_1.ref)
        self.assertEqual(resp.json['name'], self.pack_db_1.name)

    def test_get_one_doesnt_exist(self):
        resp = self.app.get('/v1/packs/doesntexistfoo', expect_errors=True)
        self.assertEqual(resp.status_int, 404)
