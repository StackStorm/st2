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

import bson
import eventlet
import mock

from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.models.db.reactor import TriggerDB
from st2common.models.system.common import ResourceReference
from st2reactor.timer.base import St2Timer
from st2tests.base import EventletTestCase
import st2tests.config as tests_config


class TestDispatcher(object):
    def __init__(self):
        self.trigger = None
        self.payload = None

    def dispatch(self, trigger, payload):
        self.trigger = trigger
        self.payload = payload

    def assert_payload(self):
        return self.payload is not None and self.payload.get('executed_at', None)


class TimerTest(EventletTestCase):
    test_trigger = None

    @classmethod
    def setUpClass(cls):
        super(TimerTest, cls).setUpClass()
        tests_config.parse_args()
        parameters = {}
        parameters['unit'] = 'seconds'
        parameters['delta'] = 1
        ref = ResourceReference.to_string_reference(SYSTEM_PACK_NAME, 'st2.IntervalTimer')
        TimerTest.test_trigger = TriggerDB(name='testtimer', pack='test', parameters=parameters,
                                           type=ref)
        TimerTest.test_trigger.id = str(bson.ObjectId())

    def test_add_remove_timer_trigger(self):
        timer = St2Timer(local_timezone='America/Los_Angeles')
        self.assertTrue(len(timer._scheduler.get_jobs()) == 0)
        timer.add_trigger(TimerTest.test_trigger)
        self.assertTrue(len(timer._scheduler.get_jobs()) == 1)
        timer.remove_trigger(TimerTest.test_trigger)
        self.assertTrue(len(timer._scheduler.get_jobs()) == 0)

    def test_emit_trigger_instance(self):
        timer = St2Timer(local_timezone='America/Los_Angeles')
        mock_dispatcher = TestDispatcher()
        setattr(timer, '_trigger_dispatcher', mock_dispatcher)
        timer._emit_trigger_instance(TimerTest.test_trigger)
        self.assertTrue(mock_dispatcher.assert_payload())

    def test_invalid_schema_timer(self):
        timer = St2Timer(local_timezone='America/Los_Angeles')
        fail_timer = copy.copy(TimerTest.test_trigger)
        del fail_timer.parameters['unit']
        timer.add_trigger(fail_timer)
        self.assertTrue(len(timer._scheduler.get_jobs()) == 0)

    def test_duplicate_timer_trigger(self):
        timer = St2Timer(local_timezone='America/Los_Angeles')
        self.assertTrue(len(timer._scheduler.get_jobs()) == 0)
        timer.add_trigger(TimerTest.test_trigger)
        self.assertTrue(len(timer._scheduler.get_jobs()) == 1)
        try:
            timer.add_trigger(TimerTest.test_trigger)
        except:
            self.assertTrue(len(timer._scheduler.get_jobs()) == 1)
            pass
        timer.remove_trigger(TimerTest.test_trigger)
        self.assertTrue(len(timer._scheduler.get_jobs()) == 0)

    @mock.patch.object(St2Timer, '_register_timer_trigger_types', mock.MagicMock())
    def test_timer_end_to_end(self):
        timer = St2Timer(local_timezone='America/Los_Angeles')
        mock_dispatcher = TestDispatcher()
        setattr(timer, '_trigger_dispatcher', mock_dispatcher)
        timer.add_trigger(TimerTest.test_trigger)

        def kickoff_timer(timer):
            timer.start()

        eventlet.spawn(kickoff_timer, timer)
        eventlet.sleep(2)
        self.assertTrue(mock_dispatcher.assert_payload())
        timer.cleanup()
