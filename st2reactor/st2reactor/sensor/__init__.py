import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Sensor(object):
    """
    """

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
