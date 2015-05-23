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


class TestTriggerTypeController(FunctionalTest):

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_is_valid_hook', mock.MagicMock(
        return_value=True))
    @mock.patch.object(WebhooksController, '_get_trigger_for_hook', mock.MagicMock(
        return_value=DUMMY_TRIGGER))
    def test_post(self):
        post_resp = self.__do_post('git', WEBHOOK_1, expect_errors=False)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    def test_post_hook_not_registered(self):
        post_resp = self.__do_post('foo', WEBHOOK_1, expect_errors=True)
        self.assertEqual(post_resp.status_int, http_client.NOT_FOUND)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    def test_st2_webhook_success(self):
        post_resp = self.__do_post('st2', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)

        post_resp = self.__do_post('st2/', ST2_WEBHOOK)
        self.assertEqual(post_resp.status_int, http_client.ACCEPTED)

    @mock.patch.object(TriggerInstancePublisher, 'publish_trigger', mock.MagicMock(
        return_value=True))
    def test_st2_webhook_body_missing_trigger(self):
        post_resp = self.__do_post('st2', {'payload': {}}, expect_errors=True)
        self.assertTrue('Trigger not specified.' in post_resp)
        self.assertEqual(post_resp.status_int, http_client.BAD_REQUEST)

    def __do_post(self, hook, webhook, expect_errors=False):
        return self.app.post_json('/v1/webhooks/' + hook, webhook, expect_errors=expect_errors)
