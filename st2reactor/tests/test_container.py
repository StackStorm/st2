import unittest2
from st2reactor.container.base import SensorContainer


class ContainerTest(unittest2.TestCase):

    def test_sensor_methods(self):
        """
        Verify start of sensors is called.
        """
        class RunTestSensor(object):
            start_call_count = 0
            setup_call_count = 0
            stop_call_count = 0

            def setup(self):
                RunTestSensor.setup_call_count += 1

            def start(self):
                RunTestSensor.start_call_count += 1

            def stop(self):
                RunTestSensor.stop_call_count += 1

            def get_trigger_types(self):
                return [
                    {'name': 'st2.dummy.t1', 'description': 'some desc', 'payload_info': ['a', 'b']}
                ]

        sensor_modules = [RunTestSensor(), RunTestSensor()]
        container = SensorContainer(sensor_instances=sensor_modules)
        container.run()
        self.assertEqual(RunTestSensor.start_call_count, len(sensor_modules),
                         'Not all Sensor.start called.')
        self.assertEqual(RunTestSensor.setup_call_count, len(sensor_modules),
                         'Not all Sensor.setup called.')

        # Now invoke shutdown and see if stop() method on sensors were called.
        container.shutdown()
        self.assertEqual(RunTestSensor.stop_call_count, len(sensor_modules),
                         'Not all Sensor.stop called.')
