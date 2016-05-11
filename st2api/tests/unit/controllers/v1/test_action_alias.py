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

from st2common.models.api.action import ActionAliasAPI

from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

FIXTURES_PACK = 'aliases'

TEST_MODELS = {
    'aliases': ['alias1.yaml', 'alias2.yaml']
}

TEST_LOAD_MODELS = {
    'aliases': ['alias3.yaml']
}

GENERIC_FIXTURES_PACK = 'generic'

TEST_LOAD_MODELS_GENERIC = {
    'aliases': ['alias3.yaml']
}


class TestActionAlias(FunctionalTest):

    models = None
    alias1 = None
    alias2 = None
    alias3 = None
    alias3_generic = None

    @classmethod
    def setUpClass(cls):
        super(TestActionAlias, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.alias1 = cls.models['aliases']['alias1.yaml']
        cls.alias2 = cls.models['aliases']['alias2.yaml']

        loaded_models = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                                     fixtures_dict=TEST_LOAD_MODELS)
        cls.alias3 = loaded_models['aliases']['alias3.yaml']

        loaded_models = FixturesLoader().load_models(fixtures_pack=GENERIC_FIXTURES_PACK,
                                                     fixtures_dict=TEST_LOAD_MODELS_GENERIC)
        cls.alias3_generic = loaded_models['aliases']['alias3.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/actionalias')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 2, '/v1/actionalias did not return all aliases.')

        retrieved_names = [alias['name'] for alias in resp.json]

        self.assertEqual(retrieved_names, [self.alias1.name, self.alias2.name],
                         'Incorrect aliases retrieved.')

    def test_get_one(self):
        resp = self.app.get('/v1/actionalias/%s' % self.alias1.id)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['name'], self.alias1.name,
                         'Incorrect aliases retrieved.')

    def test_post_delete(self):
        post_resp = self._do_post(vars(ActionAliasAPI.from_model(self.alias3)))
        self.assertEqual(post_resp.status_int, 201)

        get_resp = self.app.get('/v1/actionalias/%s' % post_resp.json['id'])
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json['name'], self.alias3.name,
                         'Incorrect aliases retrieved.')

        del_resp = self.__do_delete(post_resp.json['id'])
        self.assertEqual(del_resp.status_int, 204)

        get_resp = self.app.get('/v1/actionalias/%s' % post_resp.json['id'], expect_errors=True)
        self.assertEqual(get_resp.status_int, 404)

    def test_post_dup_name(self):
        post_resp = self._do_post(vars(ActionAliasAPI.from_model(self.alias3)))
        self.assertEqual(post_resp.status_int, 201)
        post_resp_dup_name = self._do_post(vars(ActionAliasAPI.from_model(self.alias3_generic)))
        self.assertEqual(post_resp_dup_name.status_int, 201)

        self.__do_delete(post_resp.json['id'])
        self.__do_delete(post_resp_dup_name.json['id'])

    def _do_post(self, actionalias, expect_errors=False):
        return self.app.post_json('/v1/actionalias', actionalias, expect_errors=expect_errors)

    def __do_delete(self, actionalias_id, expect_errors=False):
        return self.app.delete('/v1/actionalias/%s' % actionalias_id, expect_errors=expect_errors)
