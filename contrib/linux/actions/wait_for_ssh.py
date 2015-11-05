#!/usr/bin/env python

import time

import paramiko

from st2actions.runners.pythonrunner import Action


class BaseAction(Action):
    def run(self, keyfile, username, hostname, ssh_timeout, retries):
        key = paramiko.RSAKey.from_private_key_file(keyfile)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for index in range(retries):
            attempt = index + 1

            try:
                self.logger.debug('SSH connection attempt: %s' % (attempt))
                client.connect(hostname=hostname, username=username, pkey=key)
                return True
            except Exception as e:
                self.logger.info('Attempt %s failed (%s), sleeping...' % (attempt, str(e)))
                time.sleep(ssh_timeout)

        raise Exception('Exceeded max retries (%s)' % (retries))
