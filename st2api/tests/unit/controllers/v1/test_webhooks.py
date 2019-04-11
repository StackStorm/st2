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

import json

import mock
import six
from oslo_config import cfg

import st2common.services.triggers as trigger_service

with mock.patch.object(trigger_service, 'create_trigger_type_db', mock.MagicMock()):
    from st2api.controllers.v1.webhooks import WebhooksController, HooksHolder

from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPES
from st2common.models.api.trigger import TriggerAPI
from st2common.models.db.trigger import TriggerDB
from st2common.models.db.trigger import TriggerTypeDB
from st2common.transport.reactor import TriggerInstancePublisher

from st2tests.api import FunctionalTest

http_client = six.moves.http_client

WEBHOOK_1 = {
    'action': 'closed',
    'pull_request': {
        'merged': True
    }
}

ST2_WEBHOOK = {
    'trigger': 'git.pr-merged',
    'payload': {
        'value_str': 'string!',
        'value_int': 12345
    }
}

WEBHOOK_DATA = {
    'value_str': 'test string 1',
    'value_int': 987654,
}

# 1. Trigger which references a system webhook trigger type
DUMMY_TRIGGER_DB = TriggerDB(name='pr-merged', pack='git')
DUMMY_TRIGGER_DB.type = list(WEBHOOK_TRIGGER_TYPES.keys())[0]


DUMMY_TRIGGER_API = TriggerAPI.from_model(DUMMY_TRIGGER_DB)
DUMMY_TRIGGER_DICT = vars(DUMMY_TRIGGER_API)

# 2. Custom TriggerType object
DUMMY_TRIGGER_TYPE_DB = TriggerTypeDB(name='pr-merged', pack='git')
DUMMY_TRIGGER_TYPE_DB.payload_schema = {
    'type': 'object',
    'properties': {
        'body': {
            'properties': {
                'value_str': {
                    'type': 'string',
                    'required': True
                },
                'value_int': {
                    'type': 'integer',
                    'required': True
                }
            }
        }
    }
}

# 2. Custom TriggerType object
DUMMY_TRIGGER_TYPE_DB_2 = TriggerTypeDB(name='pr-merged', pack='git')
DUMMY_TRIGGER_TYPE_DB_2.payload_schema = {
    'type': 'object',
    'properties': {
        'body': {
            'type': 'array'
        }
    }
}


class TestWebhooksController(FunctionalTest):
    def setUp(self):
        super(TestWebhooksController, self).setUp()

        cfg.CONF.system.validate_trigger_payload = True

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_all', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    def test_get_all(self):
        get_resp = self.app.get('/v1/webhooks', expect_errors=False)
        self.assertEqual(get_resp.status_int, http_client.OK)
        self.assertEqual(get_resp.json, [DUMMY_TRIGGER_DICT])

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_post(self, dispatch_mock):
        post_resp = self.__do_post('git', WEBHOOK_1, expect_errors=False)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertTrue(dispatch_mock.call_args[1]['trace_context'].trace_tag)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    @mock.patch('st2common.services.triggers.get_trigger_type_db', mock.MagicMock(
        return_value=DUMMY_TRIGGER_TYPE_DB))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_post_with_trace(self, dispatch_mock):
        post_resp = self.__do_post('git', WEBHOOK_1, expect_errors=False,
                                   headers={'St2-Trace-Tag': 'tag1'})
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag, 'tag1')

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    def test_post_hook_not_registered(self):
        post_resp = self.__do_post('foo', WEBHOOK_1, expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.NOT_FOUND)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch('st2common.services.triggers.get_trigger_type_db', mock.MagicMock(
        return_value=DUMMY_TRIGGER_TYPE_DB))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_st2_webhook_success(self, dispatch_mock):
        post_resp = self.__do_post('st2', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertTrue(dispatch_mock.call_args[1]['trace_context'].trace_tag)

        post_resp = self.__do_post('st2/', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch('st2common.services.triggers.get_trigger_type_db', mock.MagicMock(
        return_value=DUMMY_TRIGGER_TYPE_DB))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_st2_webhook_failure_payload_validation_failed(self, dispatch_mock):
        data = {
            'trigger': 'git.pr-merged',
            'payload': 'invalid'
        }
        post_resp = self.__do_post('st2', data, expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

        expected_msg = 'Trigger payload validation failed'
        self.assertTrue(expected_msg in post_resp.json['faultstring'])

        expected_msg = "'invalid' is not of type 'object'"
        self.assertTrue(expected_msg in post_resp.json['faultstring'])

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch('st2common.services.triggers.get_trigger_type_db', mock.MagicMock(
        return_value=DUMMY_TRIGGER_TYPE_DB))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_st2_webhook_with_trace(self, dispatch_mock):
        post_resp = self.__do_post('st2', ST2_WEBHOOK, headers={'St2-Trace-Tag': 'tag1'})
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag, 'tag1')

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    def test_st2_webhook_body_missing_trigger(self):
        post_resp = self.__do_post('st2', {'payload': {}}, expect_errors=True)
        self.assertTrue('Trigger not specified.' in post_resp)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_json_request_body(self, dispatch_mock):
        # 1. Send JSON using application/json content type
        data = WEBHOOK_1
        post_resp = self.__do_post('git', data,
                                   headers={'St2-Trace-Tag': 'tag1'})
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertEqual(dispatch_mock.call_args[1]['payload']['headers']['Content-Type'],
                        'application/json')
        self.assertEqual(dispatch_mock.call_args[1]['payload']['body'], data)
        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag, 'tag1')

        # 2. Send JSON using application/json + charset content type
        data = WEBHOOK_1
        headers = {'St2-Trace-Tag': 'tag1', 'Content-Type': 'application/json; charset=utf-8'}
        post_resp = self.__do_post('git', data,
                                   headers=headers)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertEqual(dispatch_mock.call_args[1]['payload']['headers']['Content-Type'],
                        'application/json; charset=utf-8')
        self.assertEqual(dispatch_mock.call_args[1]['payload']['body'], data)
        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag, 'tag1')

        # 3. JSON content type, invalid JSON body
        data = 'invalid'
        headers = {'St2-Trace-Tag': 'tag1', 'Content-Type': 'application/json'}
        post_resp = self.app.post('/v1/webhooks/git', data, headers=headers,
                      expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)
        self.assertTrue('Failed to parse request body' in post_resp)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_form_encoded_request_body(self, dispatch_mock):
        # Send request body as form urlencoded data
        if six.PY3:
            data = {b'form': [b'test']}
        else:
            data = {'form': ['test']}

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'St2-Trace-Tag': 'tag1'
        }

        self.app.post('/v1/webhooks/git', data, headers=headers)
        self.assertEqual(dispatch_mock.call_args[1]['payload']['headers']['Content-Type'],
                        'application/x-www-form-urlencoded')
        self.assertEqual(dispatch_mock.call_args[1]['payload']['body'], data)
        self.assertEqual(dispatch_mock.call_args[1]['trace_context'].trace_tag, 'tag1')

    def test_unsupported_content_type(self):
        # Invalid / unsupported content type - should throw
        data = WEBHOOK_1
        headers = {'St2-Trace-Tag': 'tag1', 'Content-Type': 'foo/invalid'}
        post_resp = self.app.post('/v1/webhooks/git', json.dumps(data), headers=headers,
                                  expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)
        self.assertTrue('Failed to parse request body' in post_resp)
        self.assertTrue('Unsupported Content-Type' in post_resp)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(HooksHolder, 'get_triggers_for_hook', mock.MagicMock(
        return_value=[DUMMY_TRIGGER_DICT]))
    @mock.patch('st2common.services.triggers.get_trigger_type_db', mock.MagicMock(
        return_value=DUMMY_TRIGGER_TYPE_DB_2))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_custom_webhook_array_input_type(self, _):
        post_resp = self.__do_post('sample', [{'foo': 'bar'}])
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertEqual(post_resp.json, [{'foo': 'bar'}])

    def test_st2_webhook_array_webhook_array_input_type_not_valid(self):
        post_resp = self.__do_post('st2', [{'foo': 'bar'}], expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)
        self.assertEqual(post_resp.json['faultstring'],
                         'Webhook body needs to be an object, got: array')

    def test_leading_trailing_slashes(self):
        # Ideally the test should setup fixtures in DB. However, the triggerwatcher
        # that is supposed to load the models from DB does not real start given
        # eventlets etc.
        # Therefore this test is somewhat special and does not post directly.
        # This only check performed here is that even if a trigger was infact created with
        # the url containing all kinds of slashes the normalized version still work.
        # The part which does not get tested is integration with pecan since # that will
        # require hacking into the test app and force dependency on pecan internals.
        # TLDR; sorry for the ghetto test. Not sure how else to test this as a unit test.
        def get_webhook_trigger(name, url):
            trigger = TriggerDB(name=name, pack='test')
            trigger.type = list(WEBHOOK_TRIGGER_TYPES.keys())[0]
            trigger.parameters = {'url': url}
            return trigger

        test_triggers = [
            get_webhook_trigger('no_slash', 'no_slash'),
            get_webhook_trigger('with_leading_slash', '/with_leading_slash'),
            get_webhook_trigger('with_trailing_slash', '/with_trailing_slash/'),
            get_webhook_trigger('with_leading_trailing_slash', '/with_leading_trailing_slash/'),
            get_webhook_trigger('with_mixed_slash', '/with/mixed/slash/')
        ]

        controller = WebhooksController()
        for trigger in test_triggers:
            controller.add_trigger(trigger)

        self.assertTrue(controller._is_valid_hook('no_slash'))
        self.assertFalse(controller._is_valid_hook('/no_slash'))
        self.assertTrue(controller._is_valid_hook('with_leading_slash'))
        self.assertTrue(controller._is_valid_hook('with_trailing_slash'))
        self.assertTrue(controller._is_valid_hook('with_leading_trailing_slash'))
        self.assertTrue(controller._is_valid_hook('with/mixed/slash'))

    def __do_post(self, hook, webhook, expect_errors=False, headers=None):
        return self.app.post_json('/v1/webhooks/' + hook,
                                  params=webhook,
                                  expect_errors=expect_errors,
                                  headers=headers)
