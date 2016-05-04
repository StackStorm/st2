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
import traceback
import uuid

from oslo_config import cfg

from st2common import log as logging
from st2actions.runners.ssh.paramiko_ssh_runner import RUNNER_REMOTE_DIR
from st2actions.runners.ssh.paramiko_ssh_runner import BaseParallelSSHRunner
from st2common.models.system.paramiko_script_action import ParamikoRemoteScriptAction

__all__ = [
    'get_runner',

    'ParamikoRemoteScriptRunner',
]

LOG = logging.getLogger(__name__)


def get_runner():
    return ParamikoRemoteScriptRunner(str(uuid.uuid4()))


class ParamikoRemoteScriptRunner(BaseParallelSSHRunner):
    def run(self, action_parameters):
        remote_action = self._get_remote_action(action_parameters)

        LOG.debug('Executing remote action.', extra={'_action_params': remote_action})
        result = self._run(remote_action)
        LOG.debug('Executed remote action.', extra={'_result': result})
        status = self._get_result_status(result, cfg.CONF.ssh_runner.allow_partial_failure)

        return (status, result, None)

    def _run(self, remote_action):
        try:
            copy_results = self._copy_artifacts(remote_action)
        except:
            # If for whatever reason there is a top level exception,
            # we just bail here.
            error = 'Failed copying content to remote boxes.'
            LOG.exception(error)
            _, ex, tb = sys.exc_info()
            copy_results = self._generate_error_results(' '.join([error, str(ex)]), tb)
            return copy_results

        try:
            exec_results = self._run_script_on_remote_host(remote_action)
            try:
                remote_dir = remote_action.get_remote_base_dir()
                LOG.debug('Deleting remote execution dir.', extra={'_remote_dir': remote_dir})
                delete_results = self._parallel_ssh_client.delete_dir(path=remote_dir,
                                                                      force=True)
                LOG.debug('Deleted remote execution dir.', extra={'_result': delete_results})
            except:
                LOG.exception('Failed deleting remote dir.', extra={'_remote_dir': remote_dir})
            finally:
                return exec_results
        except:
            error = 'Failed executing script on remote boxes.'
            LOG.exception(error, extra={'_action_params': remote_action})
            _, ex, tb = sys.exc_info()
            exec_results = self._generate_error_results(' '.join([error, str(ex)]), tb)
            return exec_results

    def _copy_artifacts(self, remote_action):
        # First create remote execution directory.
        remote_dir = remote_action.get_remote_base_dir()
        LOG.debug('Creating remote execution dir.', extra={'_path': remote_dir})
        mkdir_result = self._parallel_ssh_client.mkdir(path=remote_action.get_remote_base_dir())

        # Copy the script to remote dir in remote host.
        local_script_abs_path = remote_action.get_local_script_abs_path()
        remote_script_abs_path = remote_action.get_remote_script_abs_path()
        file_mode = 0744
        extra = {'_local_script': local_script_abs_path, '_remote_script': remote_script_abs_path,
                 'mode': file_mode}
        LOG.debug('Copying local script to remote box.', extra=extra)
        put_result_1 = self._parallel_ssh_client.put(local_path=local_script_abs_path,
                                                     remote_path=remote_script_abs_path,
                                                     mirror_local_mode=False, mode=file_mode)

        # If `lib` exist for the script, copy that to remote host.
        local_libs_path = remote_action.get_local_libs_path_abs()
        if os.path.exists(local_libs_path):
            extra = {'_local_libs': local_libs_path, '_remote_path': remote_dir}
            LOG.debug('Copying libs to remote host.', extra=extra)
            put_result_2 = self._parallel_ssh_client.put(local_path=local_libs_path,
                                                         remote_path=remote_dir,
                                                         mirror_local_mode=True)

        result = mkdir_result or put_result_1 or put_result_2
        return result

    def _run_script_on_remote_host(self, remote_action):
        command = remote_action.get_full_command_string()
        LOG.info('Command to run: %s', command)
        results = self._parallel_ssh_client.run(command, timeout=remote_action.get_timeout())
        LOG.debug('Results from script: %s', results)
        return results

    def _get_remote_action(self, action_parameters):
        # remote script actions without entry_point don't make sense, user probably wanted to use
        # "remote-shell-cmd" action
        if not self.entry_point:
            msg = ('Action "%s" is missing "entry_point" attribute. Perhaps wanted to use '
                   '"remote-shell-script" runner?' % (self.action_name))
            raise Exception(msg)

        script_local_path_abs = self.entry_point
        pos_args, named_args = self._get_script_args(action_parameters)
        named_args = self._transform_named_args(named_args)
        env_vars = self._get_env_vars()
        remote_dir = self.runner_parameters.get(RUNNER_REMOTE_DIR,
                                                cfg.CONF.ssh_runner.remote_dir)
        remote_dir = os.path.join(remote_dir, self.liveaction_id)
        return ParamikoRemoteScriptAction(self.action_name,
                                          str(self.liveaction_id),
                                          script_local_path_abs,
                                          self.libs_dir_path,
                                          named_args=named_args,
                                          positional_args=pos_args,
                                          env_vars=env_vars,
                                          on_behalf_user=self._on_behalf_user,
                                          user=self._username,
                                          password=self._password,
                                          private_key=self._private_key,
                                          remote_dir=remote_dir,
                                          hosts=self._hosts,
                                          parallel=self._parallel,
                                          sudo=self._sudo,
                                          timeout=self._timeout,
                                          cwd=self._cwd)

    @staticmethod
    def _generate_error_results(error, tb):
        error_dict = {
            'error': error,
            'traceback': ''.join(traceback.format_tb(tb, 20)) if tb else '',
            'failed': True,
            'succeeded': False,
            'return_code': 255
        }
        return error_dict
