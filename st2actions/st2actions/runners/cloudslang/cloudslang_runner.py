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

import shlex
import uuid

import eventlet
import os
import tempfile
from oslo.config import cfg
from eventlet.green import subprocess
from st2common import log as logging
from st2actions.runners import ActionRunner
from st2actions.runners import ShellRunnerMixin
from st2common.models.system.action import ShellCommandAction
from st2common.constants.action import LIVEACTION_STATUS_SUCCEEDED
from st2common.constants.action import LIVEACTION_STATUS_FAILED
from st2common.constants.runners import LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT
import st2common.util.jsonify as jsonify


LOG = logging.getLogger(__name__)

# constants to lookup in runner_parameters.
RUNNER_PATH = 'path'
RUNNER_INPUTS = 'inputs'
RUNNER_TIMEOUT = 'timeout'


def get_runner():
    return CloudSlangRunner(str(uuid.uuid4()))


class CloudSlangRunner(ActionRunner, ShellRunnerMixin):
    """
    Runner which executes cloudslang flows and operations as single action
    """
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']

    def __init__(self, runner_id):
        super(CloudSlangRunner, self).__init__(runner_id=runner_id)

    def pre_run(self):
        self._user = cfg.CONF.system_user.user
        self._cloudslang_home = cfg.CONF.cloudslang.home_dir
        self._path = self.runner_parameters.get(RUNNER_PATH)
        self._inputs = self.runner_parameters.get(RUNNER_INPUTS)
        self._timeout = self.runner_parameters.get(RUNNER_TIMEOUT,
                                                   LOCAL_RUNNER_DEFAULT_ACTION_TIMEOUT)

    def run(self, action_parameters):
        LOG.debug('    action_parameters = %s', action_parameters)

        inputs_file = tempfile.NamedTemporaryFile()
        LOG.info(self._inputs)
        inputs_dict = dict(pair.split("=") for pair in self._inputs.split(","))
        LOG.info(inputs_dict)
        import yaml
        inputs_file.write(yaml.safe_dump(inputs_dict, default_flow_style=False))
        inputs_file.seek(0)

        for line in inputs_file:
            LOG.info(line.rstrip())

        command = self._cloudslang_home + "/bin/cslang" \
                                          " run" \
                                          " --f " + self._path + \
                                          " --if " + inputs_file.name + \
                                          " --cp " + self._cloudslang_home
        action = ShellCommandAction(name=self.action_name,
                                    action_exec_id=str(self.liveaction_id),
                                    command=command,
                                    user=self._user)
        args = action.get_full_command_string()

        env = os.environ.copy()

        LOG.info('Executing action via LocalRunner: %s', self.runner_id)
        LOG.info('[Action info] name: %s, Id: %s, command: %s, user: %s, sudo: %s' %
                 (action.name, action.action_exec_id, args, action.user, action.sudo))

        # Make sure os.setsid is called on each spawned process so that all processes
        # are in the same group.
        LOG.info("args are " + args)
        process = subprocess.Popen(args=args, stdin=None, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, shell=True,
                                   env=env, preexec_fn=os.setsid)

        error_holder = {}

        def on_timeout_expired(timeout):
            try:
                process.wait(timeout=self._timeout)
            except subprocess.TimeoutExpired:
                # Set the error prior to kill the process else the error is not picked up due
                # to eventlet scheduling.
                error_holder['error'] = 'Action failed to complete in %s seconds' % (self._timeout)
                # Action has timed out, kill the process and propagate the error. The process
                # is started as sudo -u {{system_user}} -- bash -c {{command}}. Introduction of the
                # bash means that multiple independent processes are spawned without them being
                # children of the process we have access to and this requires use of pkill.
                # Ideally os.killpg should have done the trick but for some reason that failed.
                # Note: pkill will set the returncode to 143 so we don't need to explicitly set
                # it to some non-zero value.
                try:
                    killcommand = shlex.split('sudo pkill -TERM -s %s' % process.pid)
                    subprocess.call(killcommand)
                except:
                    LOG.exception('Unable to pkill.')

        timeout_expiry = eventlet.spawn(on_timeout_expired, self._timeout)

        stdout, stderr = process.communicate()
        timeout_expiry.cancel()
        error = error_holder.get('error', None)
        exit_code = process.returncode
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

        status = LIVEACTION_STATUS_SUCCEEDED if exit_code == 0 else LIVEACTION_STATUS_FAILED
        self._log_action_completion(logger=LOG, result=result, status=status, exit_code=exit_code)
        return status, jsonify.json_loads(result, CloudSlangRunner.KEYS_TO_TRANSFORM), None
