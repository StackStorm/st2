#!/usr/bin/env python

# Copyright 2020 The StackStorm Authors.
# Copyright 2019 Extreme Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time

import six
from oslo_config import cfg

from st2common.runners.base_action import Action
from st2common.runners.paramiko_ssh import ParamikoSSHClient


class BaseAction(Action):
    def run(
        self,
        hostname,
        port,
        username,
        password=None,
        keyfile=None,
        ssh_timeout=5,
        sleep_delay=20,
        retries=10,
    ):
        # Note: If neither password nor key file is provided, we try to use system user
        # key file
        if not password and not keyfile:
            keyfile = cfg.CONF.system_user.ssh_key_file
            self.logger.info(
                'Neither "password" nor "keyfile" parameter provided, '
                'defaulting to using "%s" key file' % (keyfile)
            )

        client = ParamikoSSHClient(
            hostname=hostname,
            port=port,
            username=username,
            password=password,
            key_files=keyfile,
            timeout=ssh_timeout,
        )

        for index in range(retries):
            attempt = index + 1

            try:
                self.logger.debug("SSH connection attempt: %s" % (attempt))
                client.connect()
                return True
            except Exception as e:
                self.logger.info(
                    "Attempt %s failed (%s), sleeping for %s seconds..."
                    % (attempt, six.text_type(e), sleep_delay)
                )
                time.sleep(sleep_delay)

        raise Exception("Exceeded max retries (%s)" % (retries))
