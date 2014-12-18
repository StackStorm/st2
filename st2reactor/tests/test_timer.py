import copy

import bson
import unittest2

from st2common.constants.pack import SYSTEM_PACK_NAME
from st2common.models.db.reactor import TriggerDB
from st2common.models.system.common import ResourceReference
from st2reactor.timer.base import St2Timer
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


class TimerTest(unittest2.TestCase):
    test_trigger = None

    @classmethod
    def setUpClass(cls):
        super(TimerTest, cls).setUpClass()
        tests_config.parse_args()
        parameters = {}
        parameters['unit'] = 'seconds'
        parameters['delta'] = 30
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
