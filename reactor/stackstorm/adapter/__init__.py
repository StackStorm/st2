import abc
import six


@six.add_metaclass(abc.ABCMeta)
class AdapterBase(object):
    """

    """

    @abc.abstractmethod
    def start(self):
        """

        """
        pass