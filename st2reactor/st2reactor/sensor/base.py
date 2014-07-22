import abc
import six


@six.add_metaclass(abc.ABCMeta)
class Sensor(object):
    """
    """

    webhook = None

    def __init__(self, container_service):
        if self.webhook:
            self.webhook.container_service = container_service

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
    def get_trigger_types(self):
        """
        """
        pass
