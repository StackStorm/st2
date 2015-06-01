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

import datetime
import mock
import six

from st2common.transport.publishers import PoolPublisher
from st2common.persistence.trigger import TriggerInstance
from st2common.models.db.trigger import TriggerInstanceDB
from tests import FunctionalTest

http_client = six.moves.http_client


@mock.patch.object(PoolPublisher, 'publish', mock.MagicMock())
class TestTriggerController(FunctionalTest):

    @classmethod
    def setUpClass(cls):
        super(TestTriggerController, cls).setUpClass()
        cls._setupTriggerTypes()
        cls._setupTriggers()
        cls._setupTriggerInstances()

    def test_get_all(self):
        resp = self.app.get('/v1/triggerinstances')
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), self.triggerinstance_count, 'Get all failure.')

    def test_get_all_limit(self):
        limit = 1
        resp = self.app.get('/v1/triggerinstances?limit=%d' % limit)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), limit, 'Get all failure. Length doesn\'t match limit.')

    def test_get_one(self):
        triggerinstance_id = str(self.triggerinstance_1.id)
        resp = self._do_get_one(triggerinstance_id)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(self._get_id(resp), triggerinstance_id)

        triggerinstance_id = str(self.triggerinstance_2.id)
        resp = self._do_get_one(triggerinstance_id)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(self._get_id(resp), triggerinstance_id)

        triggerinstance_id = str(self.triggerinstance_3.id)
        resp = self._do_get_one(triggerinstance_id)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(self._get_id(resp), triggerinstance_id)

    def test_get_one_fail(self):
        resp = self._do_get_one('1')
        self.assertEqual(resp.status_int, http_client.NOT_FOUND)

    @classmethod
    def _setupTriggerTypes(cls):
        TRIGGERTYPE_0 = {
            'name': 'st2.test.triggertype0',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
            'parameters_schema': {}
        }
        TRIGGERTYPE_1 = {
            'name': 'st2.test.triggertype1',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
        }
        TRIGGERTYPE_2 = {
            'name': 'st2.test.triggertype2',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'payload_schema': {'tp1': None, 'tp2': None, 'tp3': None},
            'parameters_schema': {'param1': {'type': 'object'}}
        }
        cls.app.post_json('/v1/triggertypes', TRIGGERTYPE_0, expect_errors=False)
        cls.app.post_json('/v1/triggertypes', TRIGGERTYPE_1, expect_errors=False)
        cls.app.post_json('/v1/triggertypes', TRIGGERTYPE_2, expect_errors=False)

    @classmethod
    def _setupTriggers(cls):
        TRIGGER_0 = {
            'name': 'st2.test.trigger0',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'type': 'dummy_pack_1.st2.test.triggertype0',
            'parameters': {}
        }

        TRIGGER_1 = {
            'name': 'st2.test.trigger1',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'type': 'dummy_pack_1.st2.test.triggertype1',
            'parameters': {}
        }

        TRIGGER_2 = {
            'name': 'st2.test.trigger2',
            'pack': 'dummy_pack_1',
            'description': 'test trigger',
            'type': 'dummy_pack_1.st2.test.triggertype2',
            'parameters': {
                'param1': {
                    'foo': 'bar'
                }
            }
        }
        cls.app.post_json('/v1/triggers', TRIGGER_0, expect_errors=False)
        cls.app.post_json('/v1/triggers', TRIGGER_1, expect_errors=False)
        cls.app.post_json('/v1/triggers', TRIGGER_2, expect_errors=False)

    @classmethod
    def _setupTriggerInstances(cls):
        cls.triggerinstance_count = 0
        cls.triggerinstance_1 = cls._create_trigger_instance(
            'dummy_pack_1.st2.test.trigger0',
            {'tp1': 1, 'tp2': 2, 'tp3': 3})
        cls.triggerinstance_2 = cls._create_trigger_instance(
            'dummy_pack_1.st2.test.trigger1',
            {'tp1': 'a', 'tp2': 'b', 'tp3': 'c'})
        cls.triggerinstance_3 = cls._create_trigger_instance(
            'dummy_pack_1.st2.test.trigger2',
            {'tp1': None, 'tp2': None, 'tp3': None})

    @classmethod
    def _create_trigger_instance(cls, trigger_ref, payload):
        trigger_instance = TriggerInstanceDB()
        trigger_instance.trigger = trigger_ref
        trigger_instance.payload = payload
        trigger_instance.occurrence_time = datetime.datetime.utcnow()
        created = TriggerInstance.add_or_update(trigger_instance)
        cls.triggerinstance_count += 1
        return created

    @staticmethod
    def _get_id(resp):
        return resp.json['id']

    def _do_get_one(self, triggerinstance_id):
        return self.app.get('/v1/triggerinstances/%s' % triggerinstance_id, expect_errors=True)
