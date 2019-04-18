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

import copy

import mock
import six
from oslo_config import cfg

from st2common.constants.rules import RULE_TYPE_STANDARD, RULE_TYPE_BACKSTOP
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.persistence.trigger import Trigger
from st2common.models.system.common import ResourceReference
from st2common.transport.publishers import PoolPublisher
from st2api.controllers.v1.rules import RuleController
from st2tests.fixturesloader import FixturesLoader

from st2tests.api import FunctionalTest
from st2tests.api import APIControllerWithIncludeAndExcludeFilterTestCase

http_client = six.moves.http_client

TEST_FIXTURES = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml'],
    'triggers': ['trigger1.yaml'],
    'triggertypes': ['triggertype1.yaml', 'triggertype_with_parameters_2.yaml']
}

FIXTURES_PACK = 'generic'


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class RulesControllerTestCase(FunctionalTest, APIControllerWithIncludeAndExcludeFilterTestCase):
    get_all_path = '/v1/rules'
    controller_cls = RuleController
    include_attribute_field_name = 'criteria'
    exclude_attribute_field_name = 'enabled'

    VALIDATE_TRIGGER_PAYLOAD = None

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(RulesControllerTestCase, cls).setUpClass()

        # Previously, cfg.CONF.system.validate_trigger_payload was set to False explicitly
        # here. Instead, we store original value so that the default is used, and if unit
        # test modifies this, we can set it to what it was (preserve test atomicity)
        cls.VALIDATE_TRIGGER_PAYLOAD = cfg.CONF.system.validate_trigger_parameters

        models = RulesControllerTestCase.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        RulesControllerTestCase.RUNNER_TYPE = models['runners']['testrunner1.yaml']
        RulesControllerTestCase.ACTION = models['actions']['action1.yaml']
        RulesControllerTestCase.TRIGGER = models['triggers']['trigger1.yaml']

        # Don't load rule into DB as that is what is being tested.
        file_name = 'rule1.yaml'
        RulesControllerTestCase.RULE_1 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'cron_timer_rule_invalid_parameters.yaml'
        RulesControllerTestCase.RULE_2 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_no_enabled_attribute.yaml'
        RulesControllerTestCase.RULE_3 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'backstop_rule.yaml'
        RulesControllerTestCase.RULE_4 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'date_timer_rule_invalid_parameters.yaml'
        RulesControllerTestCase.RULE_5 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'cron_timer_rule_invalid_parameters_1.yaml'
        RulesControllerTestCase.RULE_6 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'cron_timer_rule_invalid_parameters_2.yaml'
        RulesControllerTestCase.RULE_7 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'cron_timer_rule_invalid_parameters_3.yaml'
        RulesControllerTestCase.RULE_8 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_invalid_trigger_parameter_type.yaml'
        RulesControllerTestCase.RULE_9 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_trigger_with_no_parameters.yaml'
        RulesControllerTestCase.RULE_10 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule_invalid_trigger_parameter_type_default_cfg.yaml'
        RulesControllerTestCase.RULE_11 = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

        file_name = 'rule space.yaml'
        RulesControllerTestCase.RULE_SPACE = RulesControllerTestCase.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

    @classmethod
    def tearDownClass(cls):
        # Replace original configured value for trigger parameter validation
        cfg.CONF.system.validate_trigger_payload = cls.VALIDATE_TRIGGER_PAYLOAD

        RulesControllerTestCase.fixtures_loader.delete_fixtures_from_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES)
        super(RulesControllerTestCase, cls).setUpClass()

    def test_get_all_and_minus_one(self):
        post_resp_rule_1 = self.__do_post(RulesControllerTestCase.RULE_1)
        post_resp_rule_3 = self.__do_post(RulesControllerTestCase.RULE_3)

        resp = self.app.get('/v1/rules')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

        resp = self.app.get('/v1/rules/?limit=-1')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 2)

        self.__do_delete(self.__get_rule_id(post_resp_rule_1))
        self.__do_delete(self.__get_rule_id(post_resp_rule_3))

    def test_get_all_limit_negative_number(self):
        post_resp_rule_1 = self.__do_post(RulesControllerTestCase.RULE_1)
        post_resp_rule_3 = self.__do_post(RulesControllerTestCase.RULE_3)

        resp = self.app.get('/v1/rules?limit=-22', expect_errors=True)
        self.assertEqual(resp.status_int, 400)
        self.assertEqual(resp.json['faultstring'],
                         u'Limit, "-22" specified, must be a positive number.')

        self.__do_delete(self.__get_rule_id(post_resp_rule_1))
        self.__do_delete(self.__get_rule_id(post_resp_rule_3))

    def test_get_all_enabled(self):
        post_resp_rule_1 = self.__do_post(RulesControllerTestCase.RULE_1)
        post_resp_rule_3 = self.__do_post(RulesControllerTestCase.RULE_3)

        # enabled=True
        resp = self.app.get('/v1/rules?enabled=True')
        self.assertEqual(resp.status_int, http_client.OK)
        rule = resp.json[0]
        self.assertEqual(self.__get_rule_id(post_resp_rule_1), rule['id'])
        self.assertEqual(rule['enabled'], True)

        # enabled=False
        resp = self.app.get('/v1/rules?enabled=False')
        self.assertEqual(resp.status_int, http_client.OK)
        rule = resp.json[0]
        self.assertEqual(self.__get_rule_id(post_resp_rule_3), rule['id'])
        self.assertEqual(rule['enabled'], False)

        self.__do_delete(self.__get_rule_id(post_resp_rule_1))
        self.__do_delete(self.__get_rule_id(post_resp_rule_3))

    def test_get_one_by_id(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        rule_id = self.__get_rule_id(post_resp)
        get_resp = self.__do_get_one(rule_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_rule_id(get_resp), rule_id)
        self.__do_delete(rule_id)

    def test_get_one_by_ref(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        rule_name = post_resp.json['name']
        rule_pack = post_resp.json['pack']
        ref = ResourceReference.to_string_reference(name=rule_name, pack=rule_pack)
        rule_id = post_resp.json['id']
        get_resp = self.__do_get_one(ref)
        self.assertEqual(get_resp.json['name'], rule_name)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.__do_delete(rule_id)

        post_resp = self.__do_post(RulesControllerTestCase.RULE_SPACE)
        rule_name = post_resp.json['name']
        rule_pack = post_resp.json['pack']
        ref = ResourceReference.to_string_reference(name=rule_name, pack=rule_pack)
        rule_id = post_resp.json['id']
        get_resp = self.__do_get_one(ref)
        self.assertEqual(get_resp.json['name'], rule_name)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.__do_delete(rule_id)

    def test_get_one_fail(self):
        resp = self.app.get('/v1/rules/1', expect_errors=True)
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    def test_post(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_post_duplicate(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        org_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        post_resp_2 = self.__do_post(RulesControllerTestCase.RULE_1)
        self.assertEqual(post_resp_2.status_int, http_client.CONFLICT)
        self.assertEqual(post_resp_2.json['conflict-id'], org_id)
        self.__do_delete(org_id)

    def test_post_invalid_rule_data(self):
        post_resp = self.__do_post({'name': 'rule'})
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)
        expected_msg = "'trigger' is a required property"
        self.assertEqual(post_resp.json['faultstring'], expected_msg)

    def test_post_trigger_parameter_schema_validation_fails(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_2)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        if six.PY3:
            expected_msg = b'Additional properties are not allowed (\'minutex\' was unexpected)'
        else:
            expected_msg = b'Additional properties are not allowed (u\'minutex\' was unexpected)'

        self.assertTrue(expected_msg in post_resp.body)

    def test_post_trigger_parameter_schema_validation_fails_missing_required_param(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_5)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        expected_msg = b'\'date\' is a required property'
        self.assertTrue(expected_msg in post_resp.body)

    def test_post_invalid_crontimer_trigger_parameters(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_6)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        expected_msg = b'1000 is greater than the maximum of 6'
        self.assertTrue(expected_msg in post_resp.body)

        post_resp = self.__do_post(RulesControllerTestCase.RULE_7)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        expected_msg = b'Invalid weekday name \\"abcdef\\"'
        self.assertTrue(expected_msg in post_resp.body)

        post_resp = self.__do_post(RulesControllerTestCase.RULE_8)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        expected_msg = b'Invalid weekday name \\"a\\"'
        self.assertTrue(expected_msg in post_resp.body)

    def test_post_invalid_custom_trigger_parameter_trigger_param_validation_enabled(self):
        # Invalid custom trigger parameter (invalid type) and non-system trigger parameter
        # validation is enabled - trigger creation should fail
        cfg.CONF.system.validate_trigger_parameters = True

        post_resp = self.__do_post(RulesControllerTestCase.RULE_9)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        if six.PY3:
            expected_msg_1 = "Failed validating 'type' in schema['properties']['param1']:"
            expected_msg_2 = '12345 is not of type \'string\''
        else:
            expected_msg_1 = "Failed validating u'type' in schema[u'properties'][u'param1']:"
            expected_msg_2 = '12345 is not of type u\'string\''

        self.assertTrue(expected_msg_1 in post_resp.json['faultstring'])
        self.assertTrue(expected_msg_2 in post_resp.json['faultstring'])

    def test_post_invalid_custom_trigger_parameter_trigger_param_validation_disabled(self):
        # Invalid custom trigger parameter (invalid type) and non-system trigger parameter
        # validation is disabled - trigger creation should succeed
        cfg.CONF.system.validate_trigger_parameters = False

        post_resp = self.__do_post(RulesControllerTestCase.RULE_9)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

    def test_post_invalid_custom_trigger_parameter_trigger_no_parameters_schema(self):
        # Invalid custom trigger parameters, custom trigger contains no parameters_schema and as
        # such, no parameters
        # Rule creation should succeed because parameters_schema is not provided and as such,
        # validation is not performed.
        cfg.CONF.system.validate_trigger_parameters = True

        post_resp = self.__do_post(RulesControllerTestCase.RULE_10)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

    def test_post_no_enabled_attribute_disabled_by_default(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_3)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.assertFalse(post_resp.json['enabled'])
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_put(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        update_input = post_resp.json
        update_input['enabled'] = not update_input['enabled']
        put_resp = self.__do_put(self.__get_rule_id(post_resp), update_input)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.__do_delete(self.__get_rule_id(put_resp))

    def test_post_no_pack_info(self):
        rule = copy.deepcopy(RulesControllerTestCase.RULE_1)
        del rule['pack']
        post_resp = self.__do_post(rule)
        self.assertEqual(post_resp.json['pack'], DEFAULT_PACK_NAME)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_put_no_pack_info(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        test_rule = post_resp.json
        if 'pack' in test_rule:
            del test_rule['pack']
        self.assertTrue('pack' not in test_rule)
        put_resp = self.__do_put(self.__get_rule_id(post_resp), test_rule)
        self.assertEqual(put_resp.json['pack'], DEFAULT_PACK_NAME)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.__do_delete(self.__get_rule_id(put_resp))

    def test_put_fail(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        update_input = post_resp.json
        # If the id in the URL is incorrect the update will fail since id in the body is ignored.
        put_resp = self.__do_put(1, update_input)
        self.assertEqual(put_resp.status_int, http_client.NOT_FOUND)
        self.__do_delete(self.__get_rule_id(post_resp))

    def test_delete(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        del_resp = self.__do_delete(self.__get_rule_id(post_resp))
        self.assertEqual(del_resp.status_int, http_client.NO_CONTENT)

    def test_rule_with_tags(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        rule_id = self.__get_rule_id(post_resp)
        get_resp = self.__do_get_one(rule_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_rule_id(get_resp), rule_id)
        self.assertEqual(get_resp.json['tags'], RulesControllerTestCase.RULE_1['tags'])
        self.__do_delete(rule_id)

    def test_rule_without_type(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_1)
        rule_id = self.__get_rule_id(post_resp)
        get_resp = self.__do_get_one(rule_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_rule_id(get_resp), rule_id)
        assigned_rule_type = get_resp.json['type']
        self.assertTrue(assigned_rule_type, 'rule_type should be assigned')
        self.assertEqual(assigned_rule_type['ref'], RULE_TYPE_STANDARD,
                         'rule_type should be standard')
        self.__do_delete(rule_id)

    def test_rule_with_type(self):
        post_resp = self.__do_post(RulesControllerTestCase.RULE_4)
        rule_id = self.__get_rule_id(post_resp)
        get_resp = self.__do_get_one(rule_id)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(self.__get_rule_id(get_resp), rule_id)
        assigned_rule_type = get_resp.json['type']
        self.assertTrue(assigned_rule_type, 'rule_type should be assigned')
        self.assertEqual(assigned_rule_type['ref'], RULE_TYPE_BACKSTOP,
                         'rule_type should be backstop')
        self.__do_delete(rule_id)

    def test_update_rule_no_data(self):
        post_resp = self.__do_post(self.RULE_1)
        rule_1_id = self.__get_rule_id(post_resp)

        put_resp = self.__do_put(rule_1_id, {})
        expected_msg = "'name' is a required property"
        self.assertEqual(put_resp.status_code, http_client.BAD_REQUEST)
        self.assertEqual(put_resp.json['faultstring'], expected_msg)

        self.__do_delete(rule_1_id)

    def test_update_rule_missing_id_in_body(self):
        post_resp = self.__do_post(self.RULE_1)
        rule_1_id = self.__get_rule_id(post_resp)

        rule_without_id = copy.deepcopy(self.RULE_1)
        rule_without_id.pop('id', None)
        put_resp = self.__do_put(rule_1_id, rule_without_id)
        self.assertEqual(put_resp.status_int, http_client.OK)
        self.assertEqual(put_resp.json['id'], rule_1_id)

        self.__do_delete(rule_1_id)

    def _insert_mock_models(self):
        rule = copy.deepcopy(RulesControllerTestCase.RULE_1)
        rule['name'] += '-253'
        post_resp = self.__do_post(rule)
        rule_1_id = self.__get_rule_id(post_resp)
        return [rule_1_id]

    def _do_delete(self, rule_id):
        return self.__do_delete(rule_id)

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


TEST_FIXTURES_2 = {
    'runners': ['testrunner1.yaml'],
    'actions': ['action1.yaml'],
    'triggertypes': ['triggertype_with_parameter.yaml']
}


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class RulesControllerTestCaseTriggerCreator(FunctionalTest):

    fixtures_loader = FixturesLoader()

    @classmethod
    def setUpClass(cls):
        super(RulesControllerTestCaseTriggerCreator, cls).setUpClass()
        cls.models = cls.fixtures_loader.save_fixtures_to_db(
            fixtures_pack=FIXTURES_PACK, fixtures_dict=TEST_FIXTURES_2)

        # Don't load rule into DB as that is what is being tested.
        file_name = 'rule_trigger_params.yaml'
        cls.RULE_1 = cls.fixtures_loader.load_fixtures(
            fixtures_pack=FIXTURES_PACK,
            fixtures_dict={'rules': [file_name]})['rules'][file_name]

    def test_ref_count_trigger_increment(self):
        post_resp = self.__do_post(self.RULE_1)
        rule_1_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        # ref_count is not served over API. Likely a choice that will prove unwise.
        triggers = Trigger.get_all(**{'type': post_resp.json['trigger']['type']})
        self.assertEqual(len(triggers), 1, 'Exactly 1 should exist')
        self.assertEqual(triggers[0].ref_count, 1, 'ref_count should be 1')

        # different rule same params
        rule_2 = copy.copy(self.RULE_1)
        rule_2['name'] = rule_2['name'] + '-2'
        post_resp = self.__do_post(rule_2)
        rule_2_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)
        triggers = Trigger.get_all(**{'type': post_resp.json['trigger']['type']})
        self.assertEqual(len(triggers), 1, 'Exactly 1 should exist')
        self.assertEqual(triggers[0].ref_count, 2, 'ref_count should be 1')

        self.__do_delete(rule_1_id)
        self.__do_delete(rule_2_id)

    def test_ref_count_trigger_decrement(self):
        post_resp = self.__do_post(self.RULE_1)
        rule_1_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        rule_2 = copy.copy(self.RULE_1)
        rule_2['name'] = rule_2['name'] + '-2'
        post_resp = self.__do_post(rule_2)
        rule_2_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        # validate decrement
        self.__do_delete(rule_1_id)
        triggers = Trigger.get_all(**{'type': post_resp.json['trigger']['type']})
        self.assertEqual(len(triggers), 1, 'Exactly 1 should exist')
        self.assertEqual(triggers[0].ref_count, 1, 'ref_count should be 1')
        self.__do_delete(rule_2_id)

    def test_trigger_cleanup(self):
        post_resp = self.__do_post(self.RULE_1)
        rule_1_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        rule_2 = copy.copy(self.RULE_1)
        rule_2['name'] = rule_2['name'] + '-2'
        post_resp = self.__do_post(rule_2)
        rule_2_id = self.__get_rule_id(post_resp)
        self.assertEqual(post_resp.status_int, http_client.CREATED)

        triggers = Trigger.get_all(**{'type': post_resp.json['trigger']['type']})
        self.assertEqual(len(triggers), 1, 'Exactly 1 should exist')
        self.assertEqual(triggers[0].ref_count, 2, 'ref_count should be 1')

        self.__do_delete(rule_1_id)
        self.__do_delete(rule_2_id)

        # validate cleanup
        triggers = Trigger.get_all(**{'type': post_resp.json['trigger']['type']})
        self.assertEqual(len(triggers), 0, 'Exactly 1 should exist')

    @staticmethod
    def __get_rule_id(resp):
        return resp.json['id']

    def __do_get_one(self, rule_id):
        return self.app.get('/v1/rules/%s' % rule_id, expect_errors=True)

    def __do_post(self, rule):
        return self.app.post_json('/v1/rules', rule, expect_errors=True)

    def __do_put(self, rule_id, rule):
        return self.app.put_json('/v1/rules/%s' % rule_id, rule, expect_errors=True)

    def __do_delete(self, rule_id):
        return self.app.delete('/v1/rules/%s' % rule_id)
