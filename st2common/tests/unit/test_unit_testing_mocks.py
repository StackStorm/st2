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

from st2tests.mocks.sensor import MockSensorWrapper
from st2tests.mocks.sensor import MockSensorService


class MockSensorServiceTestCase(unittest2.TestCase):
    def setUp(self):
        self._mock_sensor_wrapper = MockSensorWrapper(pack='dummy', class_name='test')

    def test_dispatch(self):
        sensor_service = MockSensorService(sensor_wrapper=self._mock_sensor_wrapper)

        expected_msg = 'Trigger "nope" hasn\'t been dispatched'
        self.assertRaisesRegexp(AssertionError, expected_msg,
                                sensor_service.assertTriggerDispatched, trigger='nope')

        sensor_service.dispatch(trigger='test1', payload={'a': 'b'})
        result = sensor_service.assertTriggerDispatched(trigger='test1')
        self.assertTrue(result)
        result = sensor_service.assertTriggerDispatched(trigger='test1', payload={'a': 'b'})
        self.assertTrue(result)
        expected_msg = 'Trigger "test1" hasn\'t been dispatched'
        self.assertRaisesRegexp(AssertionError, expected_msg,
                                sensor_service.assertTriggerDispatched,
                                trigger='test1',
                                payload={'a': 'c'})

    def test_list_set_get_delete_values(self):
        sensor_service = MockSensorService(sensor_wrapper=self._mock_sensor_wrapper)

        # list_values, set_value
        result = sensor_service.list_values()
        self.assertSequenceEqual(result, [])

        sensor_service.set_value(name='t1.local', value='test1', local=True)
        sensor_service.set_value(name='t1.global', value='test1', local=False)

        result = sensor_service.list_values(local=True)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].name, 'dummy.test:t1.local')

        result = sensor_service.list_values(local=False)
        self.assertEqual(result[0].name, 'dummy.test:t1.local')
        self.assertEqual(result[1].name, 't1.global')
        self.assertEqual(len(result), 2)

        # get_value
        self.assertEqual(sensor_service.get_value('inexistent'), None)
        self.assertEqual(sensor_service.get_value(name='t1.local', local=True), 'test1')

        # delete_value
        self.assertEqual(len(sensor_service.list_values(local=True)), 1)
        self.assertEqual(sensor_service.delete_value('inexistent'), False)
        self.assertEqual(len(sensor_service.list_values(local=True)), 1)

        self.assertEqual(sensor_service.delete_value('t1.local'), True)
        self.assertEqual(len(sensor_service.list_values(local=True)), 0)
