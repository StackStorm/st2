from __future__ import absolute_import

from st2reactor.sensor.base import Sensor

typobar  # noqa


class TestSensorWithTypo(Sensor):
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
