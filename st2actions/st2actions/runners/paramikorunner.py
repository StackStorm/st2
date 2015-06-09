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

# pylint: skip-file
# Note: This module is not used.

import uuid

from st2actions.runners import ActionRunner
from st2common import log as logging
from st2common.util.ssh import SSHClient

LOG = logging.getLogger(__name__)


class SSHRunner(ActionRunner):
    def __init__(self, runner_id):
        super(SSHRunner, self).__init__(runner_id=runner_id)

    def run(self, ssh_action):
        LOG.info('Executing action via SSHRunner :%s for user: %s.' %
                 (self.runner_id, ssh_action.get_user()))
        LOG.info('Action info:: name: %s, Id: %s, command: %s, actual user: %s' % (ssh_action.name,
                 ssh_action.id, ssh_action.get_command(), ssh_action.get_user()))

        results = {}
        for host in ssh_action.get_hosts():
            result = {'succeeded': True, 'failed': False}
            try:
                ssh_client = self._get_ssh_client(host, user=ssh_action.get_user(),
                                                  pkey=ssh_action.get_pkey(),
                                                  password=ssh_action.get_password())

                result_stdout, result_stderr, ret_code = ssh_client.execute_sync(
                    ssh_action.get_command(),
                    sudo=False)

                result['stdout'] = result_stdout
                result['stderr'] = result_stderr
                result['return_code'] = ret_code

                if ret_code != 0:
                    result['succeeded'] = False
                    result['failed'] = True
            except Exception as e:
                LOG.error('Exception: %s performing ssh action: %s', e, ssh_action)
                result['failed'] = True
            finally:
                results[host] = result
        return (True, None, results)

    def _get_ssh_client(self, host, user=None, pkey=None, password=None):
        if pkey is not None:
            return SSHClient(host, user=user, key=pkey)
        return SSHClient(host, user=user, password=password)


def get_runner():
    return SSHRunner(str(uuid.uuid4()))
