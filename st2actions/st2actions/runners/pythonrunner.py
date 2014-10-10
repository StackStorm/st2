import abc
import six
import sys
import traceback
import uuid

from multiprocessing import Process, Pipe
from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.models.api.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.util import loader as action_loader


LOG = logging.getLogger(__name__)


def get_runner():
    return PythonRunner(str(uuid.uuid4()))


@six.add_metaclass(abc.ABCMeta)
class Action(object):
    """
    """

    @abc.abstractmethod
    def run(self, **kwargs):
        """
        """
        pass


class ActionWrapper(object):
    def __init__(self, entry_point, action_parameters):
        self.entry_point = entry_point
        self.action_parameters = action_parameters

    def run(self, conn):
        try:
            action = self._load_action()
            output = action.run(**self.action_parameters)
            conn.send(output)
        except:
            _, e, tb = sys.exc_info()
            conn.send({'error': str(e), 'traceback': ''.join(traceback.format_tb(tb, 20))})
            sys.exit(1)
        finally:
            conn.close()

    def _load_action(self):
        actions_kls = action_loader.register_plugin(Action, self.entry_point)
        action_kls = actions_kls[0] if actions_kls and len(actions_kls) > 0 else None
        if not action_kls:
            raise Exception('%s has no action.' % self.entry_point)
        return action_kls()


class PythonRunner(ActionRunner):

    def __init__(self, _id):
        super(PythonRunner, self).__init__()
        self._id = _id

    def pre_run(self):
        pass

    def run(self, action_parameters):
        action_wrapper = ActionWrapper(self.entry_point, action_parameters)
        parent_conn, child_conn = Pipe()
        p = Process(target=action_wrapper.run, args=(child_conn,))
        try:
            p.start()
            output = parent_conn.recv()
            p.join()
            exit_code = p.exitcode
        except:
            LOG.exception('Failed to run action.')
            _, e, tb = sys.exc_info()
            exit_code = 1
            output = {'error': str(e), 'traceback': ''.join(traceback.format_tb(tb, 20))}
        status = ACTIONEXEC_STATUS_SUCCEEDED if exit_code == 0 else ACTIONEXEC_STATUS_FAILED
        self.container_service.report_result(output)
        self.container_service.report_status(status)
        LOG.info('Action output : %s. exit_code : %s. status : %s', str(output), exit_code, status)
        return output is not None
