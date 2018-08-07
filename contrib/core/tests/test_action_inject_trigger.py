#!/usr/bin/env python

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

from __future__ import absolute_import

import mock

from st2tests.base import BaseActionTestCase

from inject_trigger import InjectTriggerAction


class InjectTriggerActionTestCase(BaseActionTestCase):
    action_cls = InjectTriggerAction

    @mock.patch('st2common.services.datastore.BaseDatastoreService.get_api_client')
    def test_inject_trigger(self, mock_get_api_client):
        mock_api_client = mock.Mock()

        mock_get_api_client.return_value = mock_api_client

        action = self.get_action_instance()

        # 1. Empty payload
        action.run(trigger='dummy_pack.trigger1')
        mock_api_client.webhooks.post_generic_webhook.assert_called_with(
            trigger='dummy_pack.trigger1',
            payload={},
            trace_tag=None
        )

        mock_api_client.webhooks.post_generic_webhook.reset()

        # 2. With payload
        action.run(trigger='dummy_pack.trigger2', payload={'foo': 'bar'})

        mock_api_client.webhooks.post_generic_webhook.assert_called_with(
            trigger='dummy_pack.trigger2',
            payload={'foo': 'bar'},
            trace_tag=None
        )

        mock_api_client.webhooks.post_generic_webhook.reset()

        # 3. With payload and trace tag
        action.run(trigger='dummy_pack.trigger3', payload={'foo': 'bar'}, trace_tag='Tag1')

        mock_api_client.webhooks.post_generic_webhook.assert_called_with(
            trigger='dummy_pack.trigger3',
            payload={'foo': 'bar'},
            trace_tag='Tag1'
        )
