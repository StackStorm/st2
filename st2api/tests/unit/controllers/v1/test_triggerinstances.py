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
import datetime

from st2common.transport.publishers import PoolPublisher
from st2common.persistence.trigger import TriggerInstance
from st2common.models.db.trigger import TriggerInstanceDB
from st2common.util import date as date_utils
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

    def test_get_all_filter_by_trigger(self):
        trigger = 'dummy_pack_1.st2.test.trigger0'
        resp = self.app.get('/v1/triggerinstances?trigger=%s' % trigger)
        self.assertEqual(resp.status_int, http_client.OK)
        self.assertEqual(len(resp.json), 1, 'Get all failure. Must get only one such instance.')

    def test_get_all_filter_by_timestamp(self):
        resp = self.app.get('/v1/triggerinstances')
        self.assertEqual(resp.status_int, http_client.OK)
        timestamp_largest = resp.json[0]['occurrence_time']
        timestamp_middle = resp.json[1]['occurrence_time']
        resp = self.app.get('/v1/triggerinstances?timestamp_gt=%s' % timestamp_largest)
        # Since we sort trigger instances by time (latest first), the previous
        # get should return no trigger instances.
        self.assertEqual(len(resp.json), 0)
        resp = self.app.get('/v1/triggerinstances?timestamp_lt=%s' % (timestamp_middle))
        self.assertEqual(len(resp.json), 1)

    def test_reemit_trigger_instance(self):
        resp = self.app.get('/v1/triggerinstances')
        self.assertEqual(resp.status_int, http_client.OK)
        instance_id = resp.json[0]['id']
        resp = self.app.post('/v1/triggerinstances/%s/re_emit' % instance_id)
        self.assertEqual(resp.status_int, http_client.OK)
        resent_message = resp.json['message']
        resent_payload = resp.json['payload']
        self.assertTrue(instance_id in resent_message)
        self.assertTrue('__context' in resent_payload)
        self.assertEqual(resent_payload['__context']['original_id'], instance_id)

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
            trigger_ref='dummy_pack_1.st2.test.trigger0',
            payload={'tp1': 1, 'tp2': 2, 'tp3': 3},
            seconds=1)
        cls.triggerinstance_2 = cls._create_trigger_instance(
            trigger_ref='dummy_pack_1.st2.test.trigger1',
            payload={'tp1': 'a', 'tp2': 'b', 'tp3': 'c'},
            seconds=2)
        cls.triggerinstance_3 = cls._create_trigger_instance(
            trigger_ref='dummy_pack_1.st2.test.trigger2',
            payload={'tp1': None, 'tp2': None, 'tp3': None},
            seconds=3)

    @classmethod
    def _create_trigger_instance(cls, trigger_ref, payload, seconds):
        # Note: We use 1 second intervals between occurence time to prevent
        # occasional test failures
        occurrence_time = date_utils.get_datetime_utc_now()
        occurrence_time = occurrence_time + datetime.timedelta(seconds=seconds)

        trigger_instance = TriggerInstanceDB()
        trigger_instance.trigger = trigger_ref
        trigger_instance.payload = payload
        trigger_instance.occurrence_time = occurrence_time
        created = TriggerInstance.add_or_update(trigger_instance)
        cls.triggerinstance_count += 1
        return created

    @staticmethod
    def _get_id(resp):
        return resp.json['id']

    def _do_get_one(self, triggerinstance_id):
        return self.app.get('/v1/triggerinstances/%s' % triggerinstance_id, expect_errors=True)
