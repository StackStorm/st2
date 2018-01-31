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

from __future__ import absolute_import
import os
import re
import sys
import json
import uuid
import functools
from StringIO import StringIO
from subprocess import list2cmdline

from eventlet.green import subprocess
from oslo_config import cfg

from st2common import log as logging
from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata
from st2common.util.green.shell import run_command
from st2common.constants.action import ACTION_OUTPUT_RESULT_DELIMITER
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.action import LIVEACTION_STATUS_TIMED_OUT
from st2common.constants.runners import PYTHON_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE
from st2common.constants.error_messages import PACK_VIRTUALENV_DOESNT_EXIST
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT
from st2common.constants.runners import PYTHON_RUNNER_DEFAULT_LOG_LEVEL
from st2common.constants.system import API_URL_ENV_VARIABLE_NAME
from st2common.constants.system import AUTH_TOKEN_ENV_VARIABLE_NAME
from st2common.util.api import get_full_public_api_url
from st2common.util.pack import get_pack_common_libs_path_for_pack_ref
from st2common.util.sandboxing import get_sandbox_path
from st2common.util.sandboxing import get_sandbox_python_path
from st2common.util.sandboxing import get_sandbox_python_binary_path
from st2common.util.sandboxing import get_sandbox_virtualenv_path
from st2common.runners import python_action_wrapper
from st2common.services.action import store_execution_output_data
from st2common.runners.utils import make_read_and_store_stream_func

__all__ = [
    'PythonRunner',

    'get_runner',
    'get_metadata',
]

LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters.
RUNNER_ENV = 'env'
RUNNER_TIMEOUT = 'timeout'
RUNNER_LOG_LEVEL = 'log_level'

# Environment variables which can't be specified by the user
BLACKLISTED_ENV_VARS = [
    # We don't allow user to override PYTHONPATH since this would break things
    'pythonpath'
]

BASE_DIR = os.path.dirname(os.path.abspath(python_action_wrapper.__file__))
WRAPPER_SCRIPT_NAME = 'python_action_wrapper.py'
WRAPPER_SCRIPT_PATH = os.path.join(BASE_DIR, WRAPPER_SCRIPT_NAME)


class PythonRunner(ActionRunner):

    def __init__(self, runner_id, config=None, timeout=PYTHON_RUNNER_DEFAULT_ACTION_TIMEOUT,
                 log_level=None, sandbox=True):

        """
        :param timeout: Action execution timeout in seconds.
        :type timeout: ``int``

        :param log_level: Log level to use for the child actions.
        :type log_level: ``str``

        :param sandbox: True to use python binary from pack-specific virtual environment for the
                        child action False to use a default system python binary from PATH.
        :type sandbox: ``bool``
        """
        super(PythonRunner, self).__init__(runner_id=runner_id)
        self._config = config
        self._timeout = timeout
        self._enable_common_pack_libs = cfg.CONF.packs.enable_common_libs or False
        self._log_level = log_level or cfg.CONF.actionrunner.python_runner_log_level
        self._sandbox = sandbox

    def pre_run(self):
        super(PythonRunner, self).pre_run()

        # TODO: This is awful, but the way "runner_parameters" and other variables get assigned on
        # the runner instance is even worse. Those arguments should be passed to the constructor.
        self._env = self.runner_parameters.get(RUNNER_ENV, {})
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT, self._timeout)
        self._log_level = self.runner_parameters.get(RUNNER_LOG_LEVEL, self._log_level)

        if self._log_level == PYTHON_RUNNER_DEFAULT_LOG_LEVEL:
            self._log_level = cfg.CONF.actionrunner.python_runner_log_level

    def run(self, action_parameters):
        LOG.debug('Running pythonrunner.')
        LOG.debug('Getting pack name.')
        pack = self.get_pack_ref()
        LOG.debug('Getting user.')
        user = self.get_user()
        LOG.debug('Serializing parameters.')
        serialized_parameters = json.dumps(action_parameters) if action_parameters else ''
        LOG.debug('Getting virtualenv_path.')
        virtualenv_path = get_sandbox_virtualenv_path(pack=pack)
        LOG.debug('Getting python path.')
        if self._sandbox:
            python_path = get_sandbox_python_binary_path(pack=pack)
        else:
            python_path = sys.executable

        LOG.debug('Checking virtualenv path.')
        if virtualenv_path and not os.path.isdir(virtualenv_path):
            format_values = {'pack': pack, 'virtualenv_path': virtualenv_path}
            msg = PACK_VIRTUALENV_DOESNT_EXIST % format_values
            LOG.error('virtualenv_path set but not a directory: %s', msg)
            raise Exception(msg)

        LOG.debug('Checking entry_point.')
        if not self.entry_point:
            LOG.error('Action "%s" is missing entry_point attribute' % (self.action.name))
            raise Exception('Action "%s" is missing entry_point attribute' % (self.action.name))

        # Note: We pass config as command line args so the actual wrapper process is standalone
        # and doesn't need access to db
        LOG.debug('Setting args.')
        args = [
            python_path,
            '-u',  # unbuffered mode so streaming mode works as expected
            WRAPPER_SCRIPT_PATH,
            '--pack=%s' % (pack),
            '--file-path=%s' % (self.entry_point),
            '--parameters=%s' % (serialized_parameters),
            '--user=%s' % (user),
            '--parent-args=%s' % (json.dumps(sys.argv[1:])),
        ]

        if self._config:
            args.append('--config=%s' % (json.dumps(self._config)))

        if self._log_level != PYTHON_RUNNER_DEFAULT_LOG_LEVEL:
            # We only pass --log-level parameter if non default log level value is specified
            args.append('--log-level=%s' % (self._log_level))

        # We need to ensure all the st2 dependencies are also available to the
        # subprocess
        LOG.debug('Setting env.')
        env = os.environ.copy()
        env['PATH'] = get_sandbox_path(virtualenv_path=virtualenv_path)

        sandbox_python_path = get_sandbox_python_path(inherit_from_parent=True,
                                                      inherit_parent_virtualenv=True)

        if self._enable_common_pack_libs:
            try:
                pack_common_libs_path = get_pack_common_libs_path_for_pack_ref(pack_ref=pack)
            except Exception:
                # There is no MongoDB connection available in Lambda and pack common lib
                # functionality is not also mandatory for Lambda so we simply ignore those errors.
                # Note: We should eventually refactor this code to make runner standalone and not
                # depend on a db connection (as it was in the past) - this param should be passed
                # to the runner by the action runner container
                pack_common_libs_path = None
        else:
            pack_common_libs_path = None

        if self._enable_common_pack_libs and pack_common_libs_path:
            env['PYTHONPATH'] = pack_common_libs_path + ':' + sandbox_python_path
        else:
            env['PYTHONPATH'] = sandbox_python_path

        # Include user provided environment variables (if any)
        user_env_vars = self._get_env_vars()
        env.update(user_env_vars)

        # Include common st2 environment variables
        st2_env_vars = self._get_common_action_env_variables()
        env.update(st2_env_vars)
        datastore_env_vars = self._get_datastore_access_env_vars()
        env.update(datastore_env_vars)

        stdout = StringIO()
        stderr = StringIO()

        store_execution_stdout_line = functools.partial(store_execution_output_data,
                                                        output_type='stdout')
        store_execution_stderr_line = functools.partial(store_execution_output_data,
                                                        output_type='stderr')

        read_and_store_stdout = make_read_and_store_stream_func(execution_db=self.execution,
            action_db=self.action, store_data_func=store_execution_stdout_line)
        read_and_store_stderr = make_read_and_store_stream_func(execution_db=self.execution,
            action_db=self.action, store_data_func=store_execution_stderr_line)

        command_string = list2cmdline(args)
        LOG.debug('Running command: PATH=%s PYTHONPATH=%s %s' % (env['PATH'], env['PYTHONPATH'],
                                                                 command_string))
        exit_code, stdout, stderr, timed_out = run_command(cmd=args, stdout=subprocess.PIPE,
                                                           stderr=subprocess.PIPE, shell=False,
                                                           env=env,
                                                           timeout=self._timeout,
                                                           read_stdout_func=read_and_store_stdout,
                                                           read_stderr_func=read_and_store_stderr,
                                                           read_stdout_buffer=stdout,
                                                           read_stderr_buffer=stderr)
        LOG.debug('Returning values: %s, %s, %s, %s' % (exit_code, stdout, stderr, timed_out))
        LOG.debug('Returning.')
        return self._get_output_values(exit_code, stdout, stderr, timed_out)

    def _get_output_values(self, exit_code, stdout, stderr, timed_out):
        """
        Return sanitized output values.

        :return: Tuple with status, output and None

        :rtype: ``tuple``
        """
        if timed_out:
            error = 'Action failed to complete in %s seconds' % (self._timeout)
        else:
            error = None

        if exit_code == PYTHON_RUNNER_INVALID_ACTION_STATUS_EXIT_CODE:
            # TODO: Mark as failed instead
            raise ValueError(stderr)

        if ACTION_OUTPUT_RESULT_DELIMITER in stdout:
            split = stdout.split(ACTION_OUTPUT_RESULT_DELIMITER)
            assert len(split) == 3
            action_result = split[1].strip()
            stdout = split[0] + split[2]
        else:
            action_result = None

        # Parse the serialized action result object
        try:
            action_result = json.loads(action_result)
        except Exception as e:
            # Failed to de-serialize the result, probably it contains non-simple type or similar
            LOG.warning('Failed to de-serialize result "%s": %s' % (str(action_result), str(e)))

        if action_result:
            if isinstance(action_result, dict):
                result = action_result.get('result', None)
                status = action_result.get('status', None)
            else:
                # Failed to de-serialize action result aka result is a string
                match = re.search("'result': (.*?)$", action_result or '')

                if match:
                    action_result = match.groups()[0]

                result = action_result
                status = None
        else:
            result = 'None'
            status = None

        output = {
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
            'result': result
        }

        if error:
            output['error'] = error

        status = self._get_final_status(action_status=status, timed_out=timed_out,
                                        exit_code=exit_code)
        return (status, output, None)

    def _get_final_status(self, action_status, timed_out, exit_code):
        """
        Return final status based on action's status, time out value and
        exit code. Example: succeeded, failed, timeout.

        :return: status

        :rtype: ``str``
        """
        if action_status is not None:
            if exit_code == 0 and action_status is True:
                status = LIVEACTION_STATUS_SUCCEEDED
            elif exit_code == 0 and action_status is False:
                status = LIVEACTION_STATUS_FAILED
            else:
                status = LIVEACTION_STATUS_FAILED
        else:
            if exit_code == 0:
                status = LIVEACTION_STATUS_SUCCEEDED
            else:
                status = LIVEACTION_STATUS_FAILED

        if timed_out:
            status = LIVEACTION_STATUS_TIMED_OUT

        return status

    def _get_env_vars(self):
        """
        Return sanitized environment variables which will be used when launching
        a subprocess.

        :rtype: ``dict``
        """
        env_vars = {}

        if self._env:
            env_vars.update(self._env)

        # Remove "blacklisted" environment variables
        to_delete = []
        for key, value in env_vars.items():
            if key.lower() in BLACKLISTED_ENV_VARS:
                to_delete.append(key)

        for key in to_delete:
            LOG.debug('User specified environment variable "%s" which is being ignored...' %
                      (key))
            del env_vars[key]

        return env_vars

    def _get_datastore_access_env_vars(self):
        """
        Return environment variables so datastore access using client (from st2client)
        is possible with actions. This is done to be compatible with sensors.

        :rtype: ``dict``
        """
        env_vars = {}
        if self.auth_token:
            env_vars[AUTH_TOKEN_ENV_VARIABLE_NAME] = self.auth_token.token
        env_vars[API_URL_ENV_VARIABLE_NAME] = get_full_public_api_url()

        return env_vars


def get_runner(config=None):
    return PythonRunner(runner_id=str(uuid.uuid4()), config=config)


def get_metadata():
    return get_runner_metadata('python_runner')
