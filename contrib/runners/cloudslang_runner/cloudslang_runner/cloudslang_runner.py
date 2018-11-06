# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import uuid
import os
import tempfile
import yaml

from oslo_config import cfg
from eventlet.green import subprocess

from st2common.util.green.shell import run_command
from st2common.util.shell import kill_process
from st2common.util.shell import quote_unix
from st2common import log as logging
from st2common.runners.base import ActionRunner
from st2common.runners.base import get_metadata as get_runner_metadata
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
import st2common.util.jsonify as jsonify

__all__ = [
    'CloudSlangRunner',

    'get_runner',
    'get_metadata'
]

LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters.
RUNNER_INPUTS = 'inputs'
RUNNER_TIMEOUT = 'timeout'


class CloudSlangRunner(ActionRunner):
    """
    Runner which executes cloudslang flows and operations as single action
    """
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def __init__(self, runner_id):
        super(CloudSlangRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        self._flow_path = self.entry_point
        self._user = cfg.CONF.system_user.user
        self._cloudslang_home = cfg.CONF.cloudslang.home_dir
        self._inputs = self.runner_parameters.get(RUNNER_INPUTS, None)
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT)

    def run(self, action_parameters):
        # Note: "inputs" runner parameter has precedence over action parameters
        if self._inputs:
            inputs = self._inputs
        elif action_parameters:
            inputs = action_parameters
        else:
            inputs = None

        inputs_file_path = self._write_inputs_to_a_temp_file(inputs=inputs)
        has_inputs = (inputs_file_path is not None)

        try:
            command = self._prepare_command(has_inputs=has_inputs,
                                            inputs_file_path=inputs_file_path)

            result, status = self._run_cli_command(command)
            return (status, jsonify.json_loads(result, CloudSlangRunner.KEYS_TO_TRANSFORM), None)
        finally:
            if inputs_file_path and os.path.isfile(inputs_file_path):
                os.remove(inputs_file_path)

    def _write_inputs_to_a_temp_file(self, inputs):
        """
        Serialize inputs dictionary as YAML and write it in a temporary file.

        :param inputs: Inputs dictionary.
        :type inputs: ``dict``

        :return: Path to the temporary file.
        :rtype: ``str``
        """
        if not inputs:
            return None

        LOG.debug('Inputs dict: %s', inputs)

        inputs_file = tempfile.NamedTemporaryFile(delete=False)
        inputs_file_path = inputs_file.name
        yaml_inputs = yaml.safe_dump(inputs, default_flow_style=False)

        with open(inputs_file_path, 'w') as fp:
            fp.write(yaml_inputs)

        LOG.debug('YAML serialized inputs: %s', yaml_inputs)

        return inputs_file_path

    def _prepare_command(self, has_inputs, inputs_file_path):
        LOG.debug('CloudSlang home: %s', self._cloudslang_home)

        cloudslang_binary = os.path.join(self._cloudslang_home, 'bin/cslang')
        LOG.debug('Using CloudSlang binary: %s', cloudslang_binary)

        command_args = ['--f', self._flow_path,
                        '--cp', self._cloudslang_home]

        if has_inputs:
            command_args += ['--if', inputs_file_path]

        command = cloudslang_binary + " run " + " ".join([quote_unix(arg) for arg in command_args])
        LOG.info('Executing action via CloudSlangRunner: %s', self.runner_id)
        LOG.debug('Command is: %s', command)
        return command

    def _run_cli_command(self, command):
        exit_code, stdout, stderr, timed_out = run_command(
            cmd=command, stdin=None,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            shell=True, timeout=self._timeout, kill_func=kill_process)

        error = None
        if timed_out:
            error = 'Action failed to complete in %s seconds' % self._timeout
            exit_code = -9

        succeeded = (exit_code == 0)
        result = {
            'failed': not succeeded,
            'succeeded': succeeded,
            'return_code': exit_code,
            'stdout': stdout,
            'stderr': stderr
        }
        if error:
            result['error'] = error

        status = LIVEACTION_STATUS_SUCCEEDED if succeeded else LIVEACTION_STATUS_FAILED
        return result, status


def get_runner():
    return CloudSlangRunner(str(uuid.uuid4()))


def get_metadata():
    return get_runner_metadata('cloudslang_runner')[0]
