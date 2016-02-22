#!/usr/bin/env python

import time

from oslo_config import cfg

from st2actions.runners.pythonrunner import Action
from st2actions.runners.ssh.paramiko_ssh import ParamikoSSHClient


class BaseAction(Action):
    def run(self, hostname, port, username, password=None, keyfile=None, ssh_timeout=5,
            sleep_delay=20, retries=10):
        # Note: If neither password nor key file is provided, we try to use system user
        # key file
        if not password and not keyfile:
            keyfile = cfg.CONF.system_user.ssh_key_file
            self.logger.info('Neither "password" nor "keyfile" parameter provided, '
                             'defaulting to using "%s" key file' % (keyfile))

        client = ParamikoSSHClient(hostname=hostname, port=port, username=username,
                                   password=password, key_files=keyfile,
                                   timeout=ssh_timeout)

        for index in range(retries):
            attempt = index + 1

            try:
                self.logger.debug('SSH connection attempt: %s' % (attempt))
                client.connect()
                return True
            except Exception as e:
                self.logger.info('Attempt %s failed (%s), sleeping for %s seconds...' %
                                 (attempt, str(e), sleep_delay))
                time.sleep(sleep_delay)

        raise Exception('Exceeded max retries (%s)' % (retries))
