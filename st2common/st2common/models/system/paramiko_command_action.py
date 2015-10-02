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
import pwd

from st2common import log as logging
from st2common.models.system.action import RemoteAction
from st2common.util.shell import quote_unix

__all__ = [
    'ParamikoRemoteCommandAction',
]

LOG = logging.getLogger(__name__)

LOGGED_USER_USERNAME = pwd.getpwuid(os.getuid())[0]


class ParamikoRemoteCommandAction(RemoteAction):

    def get_full_command_string(self):
        # Note: We pass -E to sudo because we want to preserve user provided
        # environment variables
        env_str = self._get_env_vars_export_string()
        cwd = self.get_cwd()

        if self.sudo:
            if env_str:
                command = quote_unix('%s && cd %s && %s' % (env_str, cwd, self.command))
            else:
                command = quote_unix('cd %s && %s' % (cwd, self.command))

            command = 'sudo -E -- bash -c %s' % (command)
        else:
            if self.user and self.user != LOGGED_USER_USERNAME:
                # Need to use sudo to run as a different user
                user = quote_unix(self.user)
                if env_str:
                    command = quote_unix('%s && cd %s && %s' % (env_str, cwd, self.command))
                else:
                    command = quote_unix('cd %s && %s' % (cwd, self.command))
                command = 'sudo -E -u %s -- bash -c %s' % (user, command)
            else:
                if env_str:
                    command = '%s && cd %s && %s' % (env_str, quote_unix(cwd),
                                                     quote_unix(self.command))
                else:
                    command = 'cd %s && %s' % (quote_unix(cwd), quote_unix(self.command))

        LOG.debug('Command to run on remote host will be: %s', command)
        return command
