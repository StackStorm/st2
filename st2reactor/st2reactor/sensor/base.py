import abc
import time

import six
import eventlet

__all__ = [
    'Sensor',
    'PollingSensor',

    'SensorV05Mixin',
    'PollingSensorV05Mixin'
]


@six.add_metaclass(abc.ABCMeta)
class BaseSensor(object):
    """
    Base Sensor class - not to be instantiated directly.
    """

    def __init__(self, dispatcher, config=None):
        self._dispatcher = dispatcher
        self._config = config or {}

    @abc.abstractmethod
    def setup(self):
        """
        Run the sensor initialization / setup code (if any).
        """
        pass

    @abc.abstractmethod
    def run(self):
        """
        Run the sensor.
        """
        pass

    @abc.abstractmethod
    def cleanup(self):
        """
        Run the sensor cleanup code (if any).
        """
        pass

    @abc.abstractmethod
    def add_trigger(self, trigger):
        """
        """
        pass

    @abc.abstractmethod
    def update_trigger(self, trigger):
        """
        """
        pass

    @abc.abstractmethod
    def remove_trigger(self, trigger):
        """
        """
        pass


class Sensor(BaseSensor):
    """
    Base class to be inherited from by the passive sensors.
    """

    @abc.abstractmethod
    def run(self):
        pass


class PollingSensor(BaseSensor):
    """
    Base class to be inherited from by the active sensors.

    Active sensors are the ones which periodically polling a 3rd party system
    for new information.
    """

    def __init__(self, dispatcher, config, poll_interval=5):
        super(PollingSensor, self).__init__(dispatcher=dispatcher, config=config)
        self._poll_interval = poll_interval

    def run(self):
        while True:
            self.poll()
            eventlet.sleep(self._poll_interval)

    @abc.abstractmethod
    def poll(self):
        """
        Poll 3rd party system for new information.
        """
        pass


class SensorV05Mixin(object):
    def start(self):
        self.run()

    def stop(self):
        self.cleanup()

    @abc.abstractmethod
    def get_trigger_types(self):
        """
        Return a list of available triggers exposed by this sensor.

        Note: This method has been deprecated and is only needed by sensors
        running under StackStorm v0.5.
        """
        pass


class PollingSensorV05Mixin(object):
    """
    Mixin class which should be added to polling sensor classes which still
    need to work with StackStorm v0.5.

    This class implements all the methods which are still needed by StackStorm
    v0.5.
    """

    def start(self):
        while True:
            self.poll()
            time.sleep(self._poll_interval)

    def stop(self):
        self.cleanup()

    @abc.abstractmethod
    def get_trigger_types(self):
        """
        Return a list of available triggers exposed by this sensor.

        Note: This method has been deprecated and is only needed by sensors
        running under StackStorm v0.5.
        """
        pass
