# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import abc
import json
import uuid
import logging as stdlib_logging

import six
from eventlet.green import subprocess

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import ACTIONEXEC_STATUS_SUCCEEDED, ACTIONEXEC_STATUS_FAILED
from st2common.constants.pack import DEFAULT_PACK_NAME
from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import get_sandbox_virtualenv_path


LOG = logging.getLogger(__name__)

# Default timeout (in seconds) for actions executed by Python runner
DEFAULT_ACTION_TIMEOUT = 10 * 60

# constants to lookup in runner_parameters.
RUNNER_TIMEOUT = 'timeout'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WRAPPER_SCRIPT_NAME = 'python_action_wrapper.py'
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, WRAPPER_SCRIPT_NAME)


def get_runner():
    return PythonRunner(str(uuid.uuid4()))


@six.add_metaclass(abc.ABCMeta)
class Action(object):
    """
    Base action class other Python actions should inherit from.
    """

    description = None

    def __init__(self, config=None):
        """
        :param config: Action config.
        :type config: ``dict``
        """
        self.config = config or {}
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


class PythonRunner(ActionRunner):

    def __init__(self, runner_id, timeout=DEFAULT_ACTION_TIMEOUT):
        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``
        """
        super(PythonRunner, self).__init__(runner_id=runner_id)
        self._timeout = timeout

    def pre_run(self):
        # TODO :This is awful, but the way "runner_parameters" and other variables get
        # assigned on the runner instance is even worse. Those arguments should
        # be passed to the constructor.
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)

    def run(self, action_parameters):
        pack = self.action.pack if self.action else DEFAULT_PACK_NAME
        serialized_parameters = json.dumps(action_parameters) if action_parameters else ''
        virtualenv_path = get_sandbox_virtualenv_path(pack=pack)
        python_path = get_sandbox_python_binary_path(pack=pack)

        if virtualenv_path and not os.path.isdir(virtualenv_path):
            msg = PACK_VIRTUALENV_DOESNT_EXIST % (pack, pack)
            raise Exception(msg)

        args = [
            python_path,
            WRAPPER_SCRIPT_PATH,
            '--pack=%s' % (pack),
            '--file-path=%s' % (self.entry_point),
            '--parameters=%s' % (serialized_parameters)
        ]

        # We need to ensure all the st2 dependencies are also available to the
        # subprocess
        env = os.environ.copy()
        env['PYTHONPATH'] = get_sandbox_python_path(inherit_from_parent=True,
                                                    inherit_parent_virtualenv=True)

        # Note: We are using eventlet friendly implementation of subprocess
        # which uses GreenPipe so it doesn't block
        process = subprocess.Popen(args=args, stdin=None, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=False, env=env)

        try:
            exit_code = process.wait(timeout=self._timeout)
        except subprocess.TimeoutExpired:
            # Action has timed out, kill the process and propagate the error
            # Note: process.kill() will set the returncode to -9 so we don't
            # need to explicitly set it to some non-zero value
            process.kill()
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        stdout, stderr = process.communicate()
        exit_code = process.returncode

        stream_to_process = stderr if exit_code else stdout

        if ACTION_OUTPUT_RESULT_DELIMITER in stream_to_process:
            split = stream_to_process.split(ACTION_OUTPUT_RESULT_DELIMITER)
            assert len(split) == 3
            result = split[1].strip()
            stream_to_process = split[0] = split[2]
        else:
            result = None

        try:
            result = json.loads(result)
        except:
            pass

        output = {
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'result': result
        }

        if error:
            output['error'] = error

        status = ACTIONEXEC_STATUS_SUCCEEDED if exit_code == 0 else ACTIONEXEC_STATUS_FAILED
        LOG.debug('Action output : %s. exit_code : %s. status : %s', str(output), exit_code, status)
        return (status, output)
