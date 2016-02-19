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
from tests import FunctionalTest

from st2api.controllers.v1.webhooks import WebhooksController
from st2common.constants.triggers import WEBHOOK_TRIGGER_TYPES
from st2common.models.db.trigger import TriggerDB
from st2common.transport.reactor import TriggerInstancePublisher

http_client = six.moves.http_client

WEBHOOK_1 = {
    'action': 'closed',
    'pull_request': {
        'merged': True
    }
}

ST2_WEBHOOK = {
    'trigger': 'foo.bar',
    'payload': {'ponies': 'unicorns'}
}

DUMMY_TRIGGER = TriggerDB(name='pr-merged', pack='git')
DUMMY_TRIGGER.type = WEBHOOK_TRIGGER_TYPES.keys()[0]


class TestWebhooksController(FunctionalTest):

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_get_trigger_for_hook', mock.MagicMock(
        return_value=DUMMY_TRIGGER))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_post(self, dispatch_mock):
        post_resp = self.__do_post('git', WEBHOOK_1, expect_errors=False)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertTrue(dispatch_mock.call_args[1]['trace_context'].trace_tag)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_get_trigger_for_hook', mock.MagicMock(
        return_value=DUMMY_TRIGGER))
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
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_st2_webhook_success(self, dispatch_mock):
        post_resp = self.__do_post('st2', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)
        self.assertTrue(dispatch_mock.call_args[1]['trace_context'].trace_tag)

        post_resp = self.__do_post('st2/', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
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
    @mock.patch.object(WebhooksController, '_get_trigger_for_hook', mock.MagicMock(
        return_value=DUMMY_TRIGGER))
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
    @mock.patch.object(WebhooksController, '_get_trigger_for_hook', mock.MagicMock(
        return_value=DUMMY_TRIGGER))
    @mock.patch('st2common.transport.reactor.TriggerDispatcher.dispatch')
    def test_form_encoded_request_body(self, dispatch_mock):
        # Send request body as form urlencoded data
        data = {'form': ['test']}
        self.app.post('/v1/webhooks/git', data, headers={'St2-Trace-Tag': 'tag1'})
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
            trigger.type = WEBHOOK_TRIGGER_TYPES.keys()[0]
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
