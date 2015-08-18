#!/usr/bin/env python

import paramiko
import argparse
from st2actions.runners.pythonrunner import Action
import os, yaml, json, time

class BaseAction(Action):
    def run(self, keyfile, username, hostname, ssh_timeout, retries):
        key = paramiko.RSAKey.from_private_key_file(keyfile)
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        for x in range(retries):
            try:
                client.connect(hostname=hostname, username=username, pkey=key)
                return True
            except Exception, e: 
                self.logger.info(e)
                time.sleep(ssh_timeout)
            time.sleep(20)

        raise Exception("Exceeded max retries")
