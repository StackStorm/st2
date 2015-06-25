from st2reactor.sensor.base import Sensor, PollingSensor


class TestSensor(Sensor):
    def setup(self):
        pass

    def run(self):
        pass

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass


class TestPollingSensor(PollingSensor):
    def setup(self):
        pass

    def poll(self):
        pass

    def cleanup(self):
        pass

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass
