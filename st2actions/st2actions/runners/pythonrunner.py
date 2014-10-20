import os
import abc
import json
import six
import sys
import traceback
import uuid
import logging as stdlib_logging

from eventlet import greenio

from multiprocessing import Process
from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.models.api.constants import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.util import loader as action_loader
from st2common.util.config_parser import ContentPackConfigParser


LOG = logging.getLogger(__name__)

# Default timeout for actions executed by Python runner
DEFAULT_ACTION_TIMEOUT = 10 * 60


def get_runner():
    return PythonRunner(str(uuid.uuid4()))


@six.add_metaclass(abc.ABCMeta)
class Action(object):
    """
    Base action class other Python actions should inherit from.
    """

    description = None

    def __init__(self, config):
        """
        :param config: Action config.
        :type config: ``dict``
        """
        self.config = config
        self.logger = self._set_up_logger()

    @abc.abstractmethod
    def run(self, **kwargs):
        pass

    def _set_up_logger(self):
        """
        Set up a logger which logs all the messages with level DEBUG
        and above to stderr.
        """
        logger_name = 'actions.python.%s' % (self.__class__.__name__)
        logger = logging.getLogger(logger_name)

        console = stdlib_logging.StreamHandler()
        console.setLevel(stdlib_logging.DEBUG)

        formatter = stdlib_logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(stdlib_logging.DEBUG)

        return logger


class ActionWrapper(object):
    def __init__(self, content_pack, entry_point, action_parameters):
        """
        :param content_pack: Name of the content pack this action is located in.
        :type content_pack: ``str``

        :param entry_point: Full path to the action script file.
        :type entry_point: ``str``

        :param action_parameters: Action parameters.
        :type action_parameters: ``dict``
        """
        self.content_pack = content_pack
        self.entry_point = entry_point
        self.action_parameters = action_parameters

    def run(self, conn):
        try:
            action = self._load_action()
            output = action.run(**self.action_parameters)
            conn.write(str(output) + '\n')
            conn.flush()
        except Exception, e:
            _, e, tb = sys.exc_info()
            data = {'error': str(e), 'traceback': ''.join(traceback.format_tb(tb, 20))}
            data = json.dumps(data)
            conn.write(data + '\n')
            conn.flush()
            sys.exit(1)
        finally:
            conn.close()

    def _load_action(self):
        actions_kls = action_loader.register_plugin(Action, self.entry_point)
        action_kls = actions_kls[0] if actions_kls and len(actions_kls) > 0 else None

        if not action_kls:
            raise Exception('%s has no action.' % self.entry_point)

        config_parser = ContentPackConfigParser(content_pack_name=self.content_pack)
        config = config_parser.get_action_config(action_file_path=self.entry_point)

        if config:
            LOG.info('Using config "%s" for action "%s"' % (config.file_path,
                                                            self.entry_point))

            return action_kls(config=config.config)
        else:
            LOG.info('No config found for action "%s"' % (self.entry_point))
            return action_kls(config={})


class PythonRunner(ActionRunner):

    def __init__(self, _id, timeout=DEFAULT_ACTION_TIMEOUT):
        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``
        """
        super(PythonRunner, self).__init__()
        self._id = _id
        self._timeout = timeout

    def pre_run(self):
        pass

    def run(self, action_parameters):
        content_pack = self.action.content_pack if self.action else None
        action_wrapper = ActionWrapper(content_pack=content_pack,
                                       entry_point=self.entry_point,
                                       action_parameters=action_parameters)

        # We manually create a non-duplex pipe since multiprocessing.Pipe
        # doesn't play along nicely and work with eventlet
        rfd, wfd = os.pipe()

        parent_conn = greenio.GreenPipe(rfd, 'r')
        child_conn = greenio.GreenPipe(wfd, 'w', 0)

        p = Process(target=action_wrapper.run, args=(child_conn,))
        p.daemon = True

        try:
            p.start()
            p.join(self._timeout)

            if p.is_alive():
                # Process is still alive meaning the timeout has been reached
                p.terminate()
                message = 'Action failed to complete in %s seconds' % (self._timeout)
                raise Exception(message)

            output = parent_conn.readline()

            try:
                output = json.loads(output)
            except Exception:
                pass

            exit_code = p.exitcode
        except:
            LOG.exception('Failed to run action.')
            _, e, tb = sys.exc_info()
            exit_code = 1
            output = {'error': str(e), 'traceback': ''.join(traceback.format_tb(tb, 20))}
        finally:
            parent_conn.close()

        status = ACTIONEXEC_STATUS_SUCCEEDED if exit_code == 0 else ACTIONEXEC_STATUS_FAILED
        self.container_service.report_result(output)
        self.container_service.report_status(status)
        LOG.info('Action output : %s. exit_code : %s. status : %s', str(output), exit_code, status)
        return output is not None
