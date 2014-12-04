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
import six
from st2common.transport.publishers import PoolPublisher
from st2tests.fixturesloader import FixturesLoader
from tests import FunctionalTest

http_client = six.moves.http_client

TEST_FIXTURES = {
    'runners': ['testrunner1.json'],
    'actions': ['action1.json'],
    'triggers': ['trigger1.json'],
    'triggertypes': ['triggertype1.json']
}

FIXTURES_PACK = 'generic'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestRuleController(FunctionalTest):

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(TestRuleController, cls).setUpClass()
        models = TestRuleController.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        TestRuleController.RUNNER_TYPE = models['runners']['testrunner1.json']
        TestRuleController.ACTION = models['actions']['action1.json']
        TestRuleController.TRIGGER = models['triggers']['trigger1.json']

        # Don't load rule into DB as that is what is being tested.
        TestRuleController.RULE_1 = TestRuleController.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': ['rule1.json']})['rules']['rule1.json']

    @classmethod
    def tearDownClass(cls):
        TestRuleController.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        super(TestRuleController, cls).setUpClass()

    def test_get_all(self):
        resp = self.app.get('/v1/rules')
        self.assertEqual(resp.status_int, http_client.OK)

    def test_get_one(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        rule_id = self.__get_rule_id(post_resp)
        get_resp = self.__do_get_one(rule_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_rule_id(get_resp), rule_id)
        self.__do_delete(rule_id)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/rules/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_post(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_post_duplicate(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        post_resp_2 = self.__do_post(TestRuleController.RULE_1)
        self.assertEqual(post_resp_2.status_int, http_client.CONFLICT)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        update_input = post_resp.json
        update_input['enabled'] = not update_input['enabled']
        put_resp = self.__do_put(self.__get_rule_id(post_resp), update_input)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.__do_delete(self.__get_rule_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        update_input = post_resp.json
        # If the id in the URL is incorrect the update will fail since id in the body is ignored.
        put_resp = self.__do_put(1, update_input)
        self.assertEqual(put_resp.status_int, http_client.NOT_FOUND)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(TestRuleController.RULE_1)
        del_resp = self.__do_delete(self.__get_rule_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    @staticmethod
    def __get_rule_id(resp):
        return resp.json['id']

    def __do_get_one(self, rule_id):
        return self.app.get('/v1/rules/%s' % rule_id, expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_post(self, rule):
        return self.app.post_json('/v1/rules', rule, expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_put(self, rule_id, rule):
        return self.app.put_json('/v1/rules/%s' % rule_id, rule, expect_errors=True)

    @mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
    def __do_delete(self, rule_id):
        return self.app.delete('/v1/rules/%s' % rule_id)
