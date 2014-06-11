import unittest2
from st2reactor.container.base import SensorContainer
from st2reactor.sensor.base import Sensor


class ContainerTest(unittest2.TestCase):

    def test_sensor_start(self):
        """
        Verify start of sensors is called.
        """
        class RunTestSensor(Sensor):
            start_call_count = 0

            def start(self):
                RunTestSensor.start_call_count += 1

            def stop(self):
                pass

        sensor_modules = [RunTestSensor(), RunTestSensor()]
        container = SensorContainer(sensor_modules)
        container.run()
        self.assertEqual(RunTestSensor.start_call_count, len(sensor_modules),
                         'Not all Sensor.start called.')

