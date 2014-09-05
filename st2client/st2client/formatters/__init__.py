import abc
import logging
import six


LOG = logging.getLogger(__name__)


class Formatter(six.with_metaclass(abc.ABCMeta, object)):

    @classmethod
    @abc.abstractmethod
    def format(cls, subject, *args, **kwargs):
        """Override this method to customize output format for the subject.
        """
        raise NotImplementedError
