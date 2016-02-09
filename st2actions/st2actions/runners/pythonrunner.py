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
import sys
import abc
import json
import uuid

import six
from eventlet.green import subprocess

from st2actions.runners import ActionRunner
from st2common.util.green.shell import run_command
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.util.sandboxing import get_sandbox_path
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import get_sandbox_virtualenv_path
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT

__all__ = [
    'get_runner',

    'PythonRunner',
    'Action'
]

# constants to lookup in runner_parameters.
RUNNER_ENV = 'env'
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
        # logger and datastore are assigned in PythonActionWrapper._get_action_instance
        self.logger = None
        self.datastore = None

    @abc.abstractmethod
    def run(self, **kwargs):
        pass


class PythonRunner(ActionRunner):

    def __init__(self, runner_id, timeout=PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT):
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
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)

    def run(self, action_parameters):
        pack = self.get_pack_name()
        serialized_parameters = json.dumps(action_parameters) if action_parameters else ''
        virtualenv_path = get_sandbox_virtualenv_path(pack=pack)
        python_path = get_sandbox_python_binary_path(pack=pack)

        if virtualenv_path and not os.path.isdir(virtualenv_path):
            format_values = {'pack': pack, 'virtualenv_path': virtualenv_path}
            msg = PACK_VIRTUALENV_DOESNT_EXIST % format_values
            raise Exception(msg)

        if not self.entry_point:
            raise Exception('Action "%s" is missing entry_point attribute' % (self.action.name))

        args = [
            python_path,
            WRAPPER_SCRIPT_PATH,
            '--pack=%s' % (pack),
            '--file-path=%s' % (self.entry_point),
            '--parameters=%s' % (serialized_parameters),
            '--parent-args=%s' % (json.dumps(sys.argv[1:]))
        ]

        # We need to ensure all the st2 dependencies are also available to the
        # subprocess
        env = os.environ.copy()
        env['PATH'] = get_sandbox_path(virtualenv_path=virtualenv_path)
        env['PYTHONPATH'] = get_sandbox_python_path(inherit_from_parent=True,
                                                    inherit_parent_virtualenv=True)

        # Include user provided environment variables (if any)
        user_env_vars = self._get_env_vars()
        env.update(user_env_vars)

        # Include common st2 environment variables
        st2_env_vars = self._get_common_action_env_variables()
        env.update(st2_env_vars)

        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, shell=False,
                                                           env=env, timeout=self._timeout)

        if timed_out:
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        if ACTION_OUTPUT_RESULT_DELIMITER in stdout:
            split = stdout.split(ACTION_OUTPUT_RESULT_DELIMITER)
            assert len(split) == 3
            result = split[1].strip()
            stdout = split[0] + split[2]
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

        if exit_code == 0:
            status = LIVEACTION_STATUS_SUCCEEDED
        elif timed_out:
            status = LIVEACTION_STATUS_TIMED_OUT
        else:
            status = LIVEACTION_STATUS_FAILED

        return (status, output, None)

    def _get_env_vars(self):
        """
        Return sanitized environment variables which will be used when launching
        a subprocess.

        :rtype: ``dict``
        """
        # Don't allow user to override PYTHONPATH since this would break things
        blacklisted_vars = ['pythonpath']
        env_vars = {}

        if self._env:
            env_vars.update(self._env)

        # Remove "blacklisted" environment variables
        to_delete = []
        for key, value in env_vars.items():
            if key.lower() in blacklisted_vars:
                to_delete.append(key)

        for key in to_delete:
            del env_vars[key]

        return env_vars
