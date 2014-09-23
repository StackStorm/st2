import six
import abc

from st2actions import handlers
from st2common import log as logging


LOG = logging.getLogger(__name__)


@six.add_metaclass(abc.ABCMeta)
class ActionRunner(object):
    """
        The interface that must be implemented by each StackStorm
        Action Runner implementation.
    """

    def __init__(self):
        self.container_service = None
        self.runner_parameters = None
        self.action = None
        self.action_name = None
        self.action_execution_id = None
        self.entry_point = None
        self.context = None
        self.callback = None

    @abc.abstractmethod
    def pre_run(self):
        raise NotImplementedError()

    # Run will need to take an action argument
    # Run may need result data argument
    @abc.abstractmethod
    def run(self, action_parameters):
        raise NotImplementedError()

    def post_run(self):
        if self.callback and not (set(['url', 'source']) - set(self.callback.keys())):
            handler = handlers.get_handler(self.callback['source'])
            handler.callback(self.callback['url'],
                             self.context,
                             self.container_service.get_status(),
                             self.container_service.get_result())

    def __str__(self):
        attrs = ', '.join(['%s=%s' % (k, v) for k, v in six.iteritems(self.__dict__)])
        return '%s@%s(%s)' % (self.__class__.__name__, str(id(self)), attrs)
