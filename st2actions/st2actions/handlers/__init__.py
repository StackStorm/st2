import abc
import six
import importlib

from st2common import log as logging


LOG = logging.getLogger(__name__)


def get_handler(name):
    try:
        module = importlib.import_module(HANDLERS[name], package=None)
        return module.get_handler()
    except Exception as e:
        LOG.exception('Failed to import module %s for %s. %s', HANDLERS[name], name, str(e))


@six.add_metaclass(abc.ABCMeta)
class ActionExecutionCallbackHandler(object):

    @staticmethod
    @abc.abstractmethod
    def callback(url, context, status, result):
        raise NotImplementedError()


HANDLERS = {
    'mistral': 'st2actions.handlers.mistral'
}
