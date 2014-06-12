import unittest2
from st2reactor.container.base import SensorContainer


class ContainerTest(unittest2.TestCase):

    def test_sensor_start(self):
        """
        Verify start of sensors is called.
        """
        class RunTestSensor(object):
            start_call_count = 0

            def start(self):
                RunTestSensor.start_call_count += 1

            def stop(self):
                pass

            def get_trigger_types(self):
                return [
                    {'name': 'st2.dummy.t1', 'description': 'some desc', 'payload_info': ['a', 'b']}
                ]

        sensor_modules = [RunTestSensor(), RunTestSensor()]
        container = SensorContainer(sensor_modules)
        container.run()
        self.assertEqual(RunTestSensor.start_call_count, len(sensor_modules),
                         'Not all Sensor.start called.')

