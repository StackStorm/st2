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

import unittest2

from st2common.models.api.notification import NotificationsHelper


class NotificationsHelperTestCase(unittest2.TestCase):

    def test_model_transformations(self):
        notify = {}

        notify_model = NotificationsHelper.to_model(notify)
        self.assertEqual(notify_model.on_success, None)
        self.assertEqual(notify_model.on_failure, None)
        self.assertEqual(notify_model.on_complete, None)
        notify_api = NotificationsHelper.from_model(notify_model)
        self.assertEqual(notify_api, {})

        notify['on-complete'] = {
            'message': 'Action completed.',
            'routes': [
                '66'
            ],
            'data': {
                'foo': '{{foo}}',
                'bar': 1,
                'baz': [1, 2, 3]
            }
        }
        notify['on-success'] = {
            'message': 'Action succeeded.',
            'routes': [
                '100'
            ],
            'data': {
                'foo': '{{foo}}',
                'bar': 1,
            }
        }
        notify_model = NotificationsHelper.to_model(notify)
        self.assertEqual(notify['on-complete']['message'], notify_model.on_complete.message)
        self.assertDictEqual(notify['on-complete']['data'], notify_model.on_complete.data)
        self.assertListEqual(notify['on-complete']['routes'], notify_model.on_complete.routes)
        self.assertEqual(notify['on-success']['message'], notify_model.on_success.message)
        self.assertDictEqual(notify['on-success']['data'], notify_model.on_success.data)
        self.assertListEqual(notify['on-success']['routes'], notify_model.on_success.routes)

        notify_api = NotificationsHelper.from_model(notify_model)
        self.assertEqual(notify['on-complete']['message'], notify_api['on-complete']['message'])
        self.assertDictEqual(notify['on-complete']['data'], notify_api['on-complete']['data'])
        self.assertListEqual(notify['on-complete']['routes'], notify_api['on-complete']['routes'])
        self.assertEqual(notify['on-success']['message'], notify_api['on-success']['message'])
        self.assertDictEqual(notify['on-success']['data'], notify_api['on-success']['data'])
        self.assertListEqual(notify['on-success']['routes'], notify_api['on-success']['routes'])

    def test_model_transformations_missing_fields(self):
        notify = {}

        notify_model = NotificationsHelper.to_model(notify)
        self.assertEqual(notify_model.on_success, None)
        self.assertEqual(notify_model.on_failure, None)
        self.assertEqual(notify_model.on_complete, None)
        notify_api = NotificationsHelper.from_model(notify_model)
        self.assertEqual(notify_api, {})

        notify['on-complete'] = {
            'routes': [
                '66'
            ],
            'data': {
                'foo': '{{foo}}',
                'bar': 1,
                'baz': [1, 2, 3]
            }
        }
        notify['on-success'] = {
            'routes': [
                '100'
            ],
            'data': {
                'foo': '{{foo}}',
                'bar': 1,
            }
        }
        notify_model = NotificationsHelper.to_model(notify)
        self.assertDictEqual(notify['on-complete']['data'], notify_model.on_complete.data)
        self.assertListEqual(notify['on-complete']['routes'], notify_model.on_complete.routes)
        self.assertDictEqual(notify['on-success']['data'], notify_model.on_success.data)
        self.assertListEqual(notify['on-success']['routes'], notify_model.on_success.routes)

        notify_api = NotificationsHelper.from_model(notify_model)
        self.assertDictEqual(notify['on-complete']['data'], notify_api['on-complete']['data'])
        self.assertListEqual(notify['on-complete']['routes'], notify_api['on-complete']['routes'])
        self.assertDictEqual(notify['on-success']['data'], notify_api['on-success']['data'])
        self.assertListEqual(notify['on-success']['routes'], notify_api['on-success']['routes'])
