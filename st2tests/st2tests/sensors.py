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

from st2tests.mocks.sensor import MockSensorWrapper
from st2tests.mocks.sensor import MockSensorService
from st2tests.pack_resource import BasePackResourceTestCase

__all__ = [
    'BaseSensorTestCase'
]


class BaseSensorTestCase(BasePackResourceTestCase):
    """
    Base class for sensor tests.

    This class provides some utility methods for verifying that a trigger has
    been dispatched, etc.
    """

    sensor_cls = None

    def setUp(self):
        super(BaseSensorTestCase, self).setUp()

        class_name = self.sensor_cls.__name__
        sensor_wrapper = MockSensorWrapper(pack='tests', class_name=class_name)
        self.sensor_service = MockSensorService(sensor_wrapper=sensor_wrapper)

    def get_sensor_instance(self, config=None, poll_interval=None):
        """
        Retrieve instance of the sensor class.
        """
        kwargs = {
            'sensor_service': self.sensor_service
        }

        if config:
            kwargs['config'] = config

        if poll_interval is not None:
            kwargs['poll_interval'] = poll_interval

        instance = self.sensor_cls(**kwargs)  # pylint: disable=not-callable
        return instance

    def get_dispatched_triggers(self):
        return self.sensor_service.dispatched_triggers

    def get_last_dispatched_trigger(self):
        return self.sensor_service.dispatched_triggers[-1]

    def assertTriggerDispatched(self, trigger, payload=None, trace_context=None):
        """
        Assert that the trigger with the provided values has been dispatched.

        :param trigger: Name of the trigger.
        :type trigger: ``str``

        :param paylod: Trigger payload (optional). If not provided, only trigger name is matched.
        type: payload: ``object``

        :param trace_context: Trigger trace context (optional). If not provided, only trigger name
                              is matched.
        type: payload: ``object``
        """
        dispatched_triggers = self.get_dispatched_triggers()
        for item in dispatched_triggers:
            trigger_matches = (item['trigger'] == trigger)

            if payload:
                payload_matches = (item['payload'] == payload)
            else:
                payload_matches = True

            if trace_context:
                trace_context_matches = (item['trace_context'] == trace_context)
            else:
                trace_context_matches = True

            if trigger_matches and payload_matches and trace_context_matches:
                return True

        msg = 'Trigger "%s" hasn\'t been dispatched' % (trigger)
        raise AssertionError(msg)
