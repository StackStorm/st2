import abc
import logging


LOG = logging.getLogger(__name__)


class Formatter(object):

    __metaclass__ = abc.ABCMeta

    @classmethod
    @abc.abstractmethod
    def format(cls, subject, *args, **kwargs):
        """Override this method to customize output format for the subject.
        """
        raise NotImplementedError
