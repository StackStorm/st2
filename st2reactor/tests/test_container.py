from st2reactor.container.base import SensorContainer
from st2tests.base import EventletTestCase


class ContainerTest(EventletTestCase):
    class RunTestSensor(object):
        def __init__(self):
            self.start_call_count = 0
            self.setup_call_count = 0
            self.stop_call_count = 0

        def setup(self):
            self.setup_call_count += 1

        def start(self):
            self.start_call_count += 1

        def stop(self):
            self.stop_call_count += 1

        def get_trigger_types(self):
            return [{
                'name': 'st2.dummy.t1',
                'description': 'some desc',
                'payload_schema': {
                    'type': 'object'
                }
            }]

    def test_sensor_methods_are_called(self):
        sensor_modules = [ContainerTest.RunTestSensor(), ContainerTest.RunTestSensor()]
        container = SensorContainer(sensor_instances=sensor_modules)
        container.run()

        for sensor in sensor_modules:
            self.assertEqual(sensor.setup_call_count, 1, 'Sensor.setup() not called.')
            self.assertEqual(sensor.start_call_count, 1, 'Sensor.start() not called.')

        # Now invoke shutdown and see if stop() method on sensors were called.
        container.shutdown()
        for sensor in sensor_modules:
            self.assertEqual(sensor.stop_call_count, 1, 'Sensor.stop() not called.')

        # Check count of running sensors in container is zero.
        self.assertEqual(container.running(), 0, 'Leak in container.')

    def test_dynamic_add_remove_sensors(self):
        container = SensorContainer()
        container.run()

        # Add a new sensor to container.
        test_sensor = ContainerTest.RunTestSensor()
        ret = container.add_sensor(test_sensor)
        self.assertEqual(ret, True, "Container must accept a new instance.")

        # Test duplicate add.
        ret = container.add_sensor(test_sensor)
        self.assertEqual(ret, False, "Container must have rejected instance.")

        # Remove the sensor added.
        ret = container.remove_sensor(test_sensor)
        self.assertEqual(ret, True, "Container must have removed this instance.")

        # Remove a sensor that doesn't exist.
        other_test_sensor = ContainerTest.RunTestSensor()
        ret = container.remove_sensor(other_test_sensor)
        self.assertEqual(ret, False, "Container shouldn\'t' have removed this instance.")

        # Wait until the greenthreads finish.
        container._pool.waitall()
        # Test that sensor methods were invoked.
        self.assertEqual(test_sensor.setup_call_count, 1, 'Sensor.setup() not called.')
        self.assertEqual(test_sensor.start_call_count, 1, 'Sensor.start() not called.')
        self.assertEqual(test_sensor.stop_call_count, 1, 'Sensor.stop() not called.')
        container.shutdown()
