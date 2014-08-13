import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Sensor(object):
    """
    """

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

    @abc.abstractmethod
    def add_trigger(self):
        """
        """
        pass

    @abc.abstractmethod
    def update_trigger(self):
        """
        """
        pass

    @abc.abstractmethod
    def remove_trigger(self):
        """
        """
        pass

    @abc.abstractmethod
    def get_trigger_types(self):
        """
        """
        pass
