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
from st2api.controllers.v1.actionalias import ActionAliasController

from st2tests.fixturesloader import FixturesLoader

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

FIXTURES_PACK = 'aliases'

TEST_MODELS = {
    'aliases': ['alias1.yaml', 'alias2.yaml', 'alias_with_undefined_jinja_in_ack_format.yaml']
}

TEST_LOAD_MODELS = {
    'aliases': ['alias3.yaml']
}

GENERIC_FIXTURES_PACK = 'generic'

TEST_LOAD_MODELS_GENERIC = {
    'aliases': ['alias3.yaml']
}


class ActionAliasControllerTestCase(FunctionalTest,
                                    APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/actionalias'
    controller_cls = ActionAliasController
    include_attribute_field_name = 'formats'
    exclude_attribute_field_name = 'result'

    models = None
    alias1 = None
    alias2 = None
    alias3 = None
    alias3_generic = None

    @classmethod
    def setUpClass(cls):
        super(ActionAliasControllerTestCase, cls).setUpClass()
        cls.models = FixturesLoader().save_fixtures_to_db(fixtures_pack=FIXTURES_PACK,
                                                          fixtures_dict=TEST_MODELS)
        cls.alias1 = cls.models['aliases']['alias1.yaml']
        cls.alias2 = cls.models['aliases']['alias2.yaml']

        loaded_models = FixturesLoader().load_models(fixtures_pack=FIXTURES_PACK,
                                                     fixtures_dict=TEST_LOAD_MODELS)
        cls.alias3 = loaded_models['aliases']['alias3.yaml']

        FixturesLoader().save_fixtures_to_db(fixtures_pack=GENERIC_FIXTURES_PACK,
                                             fixtures_dict={'aliases': ['alias7.yaml']})

        loaded_models = FixturesLoader().load_models(fixtures_pack=GENERIC_FIXTURES_PACK,
                                                     fixtures_dict=TEST_LOAD_MODELS_GENERIC)
        cls.alias3_generic = loaded_models['aliases']['alias3.yaml']

    def test_get_all(self):
        resp = self.app.get('/v1/actionalias')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 4, '/v1/actionalias did not return all aliases.')

        retrieved_names = [alias['name'] for alias in resp.json]

        self.assertEqual(retrieved_names, [self.alias1.name, self.alias2.name,
                                           'alias_with_undefined_jinja_in_ack_format',
                                           'alias7'],
                         'Incorrect aliases retrieved.')

    def test_get_all_query_param_filters(self):
        resp = self.app.get('/v1/actionalias?pack=doesntexist')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/actionalias?pack=aliases')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 3)

        for alias_api in resp.json:
            self.assertEqual(alias_api['pack'], 'aliases')

        resp = self.app.get('/v1/actionalias?pack=generic')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)

        for alias_api in resp.json:
            self.assertEqual(alias_api['pack'], 'generic')

        resp = self.app.get('/v1/actionalias?name=doesntexist')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 0)

        resp = self.app.get('/v1/actionalias?name=alias2')
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(len(resp.json), 1)
        self.assertEqual(resp.json[0]['name'], 'alias2')

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

    def test_update_existing_alias(self):
        post_resp = self._do_post(vars(ActionAliasAPI.from_model(self.alias3)))
        self.assertEqual(post_resp.status_int, 201)
        self.assertEqual(post_resp.json['name'], self.alias3['name'])

        data = vars(ActionAliasAPI.from_model(self.alias3))
        data['name'] = 'updated-alias-name'

        put_resp = self.app.put_json('/v1/actionalias/%s' % post_resp.json['id'], data)
        self.assertEqual(put_resp.json['name'], data['name'])

        get_resp = self.app.get('/v1/actionalias/%s' % post_resp.json['id'])
        self.assertEqual(get_resp.json['name'], data['name'])

        del_resp = self.__do_delete(post_resp.json['id'])
        self.assertEqual(del_resp.status_int, 204)

    def test_post_dup_name(self):
        post_resp = self._do_post(vars(ActionAliasAPI.from_model(self.alias3)))
        self.assertEqual(post_resp.status_int, 201)
        post_resp_dup_name = self._do_post(vars(ActionAliasAPI.from_model(self.alias3_generic)))
        self.assertEqual(post_resp_dup_name.status_int, 201)

        self.__do_delete(post_resp.json['id'])
        self.__do_delete(post_resp_dup_name.json['id'])

    def test_match(self):
        # No matching patterns
        data = {'command': 'hello donny'}
        resp = self.app.post_json("/v1/actionalias/match", data, expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(str(resp.json['faultstring']),
                         "Command 'hello donny' matched no patterns")

        # More than one matching pattern
        data = {'command': 'Lorem ipsum banana dolor sit pineapple amet.'}
        resp = self.app.post_json("/v1/actionalias/match", data, expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(str(resp.json['faultstring']),
                         "Command 'Lorem ipsum banana dolor sit pineapple amet.' "
                         "matched more than 1 pattern")

        # Single matching pattern - success
        data = {'command': 'run whoami on localhost1'}
        resp = self.app.post_json("/v1/actionalias/match", data)
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json['actionalias']['name'],
                         'alias_with_undefined_jinja_in_ack_format')

    def test_help(self):
        resp = self.app.get("/v1/actionalias/help")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json.get('available'), 5)

    def test_help_args(self):
        resp = self.app.get("/v1/actionalias/help?filter=.*&pack=aliases&limit=1&offset=0")
        self.assertEqual(resp.status_int, 200)
        self.assertEqual(resp.json.get('available'), 3)
        self.assertEqual(len(resp.json.get('helpstrings')), 1)

    def _insert_mock_models(self):
        alias_ids = [self.alias1['id'], self.alias2['id'], self.alias3['id'],
                     self.alias3_generic['id']]
        return alias_ids

    def _delete_mock_models(self, object_ids):
        return None

    def _do_post(self, actionalias, expect_errors=False):
        return self.app.post_json('/v1/actionalias', actionalias, expect_errors=expect_errors)

    def __do_delete(self, actionalias_id, expect_errors=False):
        return self.app.delete('/v1/actionalias/%s' % actionalias_id, expect_errors=expect_errors)
