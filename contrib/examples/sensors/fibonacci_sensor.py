import os

from st2reactor.sensor.base import PollingSensor


class FibonacciSensor(PollingSensor):

    def __init__(self, sensor_service, config,
                 poll_interval=5):
        super(FibonacciSensor, self).__init__(
            sensor_service=sensor_service,
            config=config,
            poll_interval=poll_interval
        )
        self.a = None
        self.b = None
        self.count = None
        self.logger = None

    def setup(self):
        self.a = 0
        self.b = 1
        self.count = 2
        self.logger = self.sensor_service.get_logger(name=self.__class__.__name__)

    def poll(self):
        fib = self.a + self.b
        self.logger.debug('Count: %d, a: %d, b: %d', self.count, self.a, self.b)

        payload = {
            "count": self.count,
            "fibonacci": fib,
            "pythonpath": os.environ.get("PYTHONPATH", None)
        }

        self.sensor_service.dispatch(trigger="examples.fibonacci", payload=payload)
        self.a = self.b
        self.b = fib
        self.count = self.count + 1

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        # This method is called when trigger is created
        pass

    def update_trigger(self, trigger):
        # This method is called when trigger is updated
        pass

    def remove_trigger(self, trigger):
        # This method is called when trigger is deleted
        pass
