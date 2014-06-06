import unittest2
from st2reactor.sensor.container import SensorContainer
from st2reactor.sensor import Sensor


class ContainerTest(unittest2.TestCase):

    def test_load(self):
        """
        Verify the correct no of sensors are created.
        """
        class LoadTestSensor(Sensor):
            init_count = 0

            def __init__(self):
                LoadTestSensor.init_count += 1

            def start(self):
                pass

            def stop(self):
                pass

        sensor_modules = [LoadTestSensor, LoadTestSensor]
        container = SensorContainer(sensor_modules)
        container.load()
        self.assertEqual(LoadTestSensor.init_count, len(sensor_modules),
                         'Insufficient sensors instantiated.')

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

        sensor_modules = [RunTestSensor, RunTestSensor]
        container = SensorContainer(sensor_modules)
        container.load()
        container.run()
        self.assertEqual(RunTestSensor.start_call_count, len(sensor_modules),
                         'Not all Sensor.start called.')

    def test_sensor_start_no_load(self):
        """
        Verify start of sensors is not called without load.
        """
        class RunTestSensor(Sensor):
            start_call_count = 0

            def start(self):
                RunTestSensor.start_call_count += 1

            def stop(self):
                pass

        sensor_modules = [RunTestSensor, RunTestSensor]
        container = SensorContainer(sensor_modules)
        container.run()
        self.assertEqual(RunTestSensor.start_call_count, 0,
                         'Sensor.start should not be called.')
