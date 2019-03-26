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

import st2common.services.triggers as trigger_service

with mock.patch.object(trigger_service, 'create_trigger_type_db', mock.MagicMock()):
    from st2api.controllers.v1.timers import TimersHolder

from st2common.models.system.common import ResourceReference
from st2tests.base import DbTestCase
from st2tests.fixturesloader import FixturesLoader
from st2common.constants.triggers import INTERVAL_TIMER_TRIGGER_REF, DATE_TIMER_TRIGGER_REF
from st2common.constants.triggers import CRON_TIMER_TRIGGER_REF

from st2tests.api import FunctionalTest

PACK = 'timers'
FIXTURES = {
    'triggers': ['cron1.yaml', 'date1.yaml', 'interval1.yaml', 'interval2.yaml', 'interval3.yaml']
}


class TestTimersHolder(DbTestCase):
    MODELS = None

    @classmethod
    def setUpClass(cls):
        super(TestTimersHolder, cls).setUpClass()

        loader = FixturesLoader()
        TestTimersHolder.MODELS = loader.load_fixtures(
            fixtures_pack=PACK, fixtures_dict=FIXTURES)['triggers']
        loader.save_fixtures_to_db(fixtures_pack=PACK, fixtures_dict=FIXTURES)

    def test_add_trigger(self):
        holder = TimersHolder()
        for _, model in TestTimersHolder.MODELS.items():
            holder.add_trigger(
                ref=ResourceReference.to_string_reference(pack=model['pack'], name=model['name']),
                trigger=model
            )
        self.assertEqual(len(holder._timers), 5)

    def test_remove_trigger(self):
        holder = TimersHolder()
        model = TestTimersHolder.MODELS.get('cron1.yaml', None)
        self.assertTrue(model is not None)
        ref = ResourceReference.to_string_reference(pack=model['pack'], name=model['name'])
        holder.add_trigger(ref, model)
        self.assertEqual(len(holder._timers), 1)
        holder.remove_trigger(ref, model)
        self.assertEqual(len(holder._timers), 0)

    def test_get_all(self):
        holder = TimersHolder()
        for _, model in TestTimersHolder.MODELS.items():
            holder.add_trigger(
                ref=ResourceReference.to_string_reference(pack=model['pack'], name=model['name']),
                trigger=model
            )
        self.assertEqual(len(holder.get_all()), 5)

    def test_get_all_filters_filter_by_type(self):
        holder = TimersHolder()
        for _, model in TestTimersHolder.MODELS.items():
            holder.add_trigger(
                ref=ResourceReference.to_string_reference(pack=model['pack'], name=model['name']),
                trigger=model
            )
        self.assertEqual(len(holder.get_all(timer_type=INTERVAL_TIMER_TRIGGER_REF)), 3)
        self.assertEqual(len(holder.get_all(timer_type=DATE_TIMER_TRIGGER_REF)), 1)
        self.assertEqual(len(holder.get_all(timer_type=CRON_TIMER_TRIGGER_REF)), 1)


class TestTimersController(FunctionalTest, DbTestCase):
    MODELS = None

    @classmethod
    def setUpClass(cls):
        super(TestTimersController, cls).setUpClass()

        loader = FixturesLoader()
        TestTimersController.MODELS = loader.save_fixtures_to_db(
            fixtures_pack=PACK, fixtures_dict=FIXTURES)['triggers']

    def test_timerscontroller_get_one_with_id(self):
        model = TestTimersController.MODELS['interval1.yaml']
        get_resp = self._do_get_one(model.id)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json['parameters'], model['parameters'])

    def test_timerscontroller_get_one_with_ref(self):
        model = TestTimersController.MODELS['interval1.yaml']
        ref = ResourceReference.to_string_reference(pack=model['pack'], name=model['name'])
        get_resp = self._do_get_one(ref)
        self.assertEqual(get_resp.status_int, 200)
        self.assertEqual(get_resp.json['parameters'], model['parameters'])

    def _do_get_one(self, timer_id, expect_errors=False):
        return self.app.get('/v1/timers/%s' % timer_id, expect_errors=expect_errors)
