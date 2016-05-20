import abc

import six
import eventlet

__all__ = [
    'Sensor',
    'PollingSensor'
]


@six.add_metaclass(abc.ABCMeta)
class BaseSensor(object):
    """
    Base Sensor class - not to be instantiated directly.
    """

    def __init__(self, sensor_service, config=None):
        """
        :param sensor_service: Sensor Service instance.
        :type sensor_service: :class:``st2reactor.container.sensor_wrapper.SensorService``

        :keyword config: Sensor config.
        :type config: ``dict`` or None
        """
        self._sensor_service = sensor_service  # Deprecate in the future
        self.sensor_service = sensor_service
        self._config = config or {}  # Deprecate in the future
        self.config = self._config

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
        Runs when trigger is created
        """
        pass

    @abc.abstractmethod
    def update_trigger(self, trigger):
        """
        Runs when trigger is updated
        """
        pass

    @abc.abstractmethod
    def remove_trigger(self, trigger):
        """
        Runs when trigger is deleted
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

    Active sensors periodically poll a 3rd party system for new information.
    """

    def __init__(self, sensor_service, config=None, poll_interval=5):
        super(PollingSensor, self).__init__(sensor_service=sensor_service, config=config)
        self._poll_interval = poll_interval

    @abc.abstractmethod
    def poll(self):
        """
        Poll 3rd party system for new information.
        """
        pass

    def run(self):
        while True:
            self.poll()
            eventlet.sleep(self._poll_interval)

    def get_poll_interval(self):
        """
        Retrieve current poll interval.

        :return: Current poll interval.
        :rtype: ``float``
        """
        return self._poll_interval

    def set_poll_interval(self, poll_interval):
        """
        Set the poll interval.

        :param poll_interval: Poll interval to use.
        :type poll_interval: ``float``
        """
        self._poll_interval = poll_interval
