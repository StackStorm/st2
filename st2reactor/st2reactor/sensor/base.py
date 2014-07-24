import abc
import six

from pecan.rest import RestController


@six.add_metaclass(abc.ABCMeta)
class SensorHook(RestController):

    _sensor = None
    _container_service = None

    name = abc.abstractproperty()


@six.add_metaclass(abc.ABCMeta)
class Sensor(object):
    """
    """
    schema = abc.abstractproperty()
    webhook = SensorHook

    @abc.abstractmethod
    def setup(self):
        """
        """
        pass

    @abc.abstractmethod
    def start(self):
        """
        """
        pass

    @abc.abstractmethod
    def stop(self):
        """
        """
        pass
