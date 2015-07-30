#!/usr/bin/env python2.7

import argparse
import pprint
import sys

import eventlet

from st2common.util.paramiko_ssh import ParamikoSSHClient

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


class ParallelSSHClient(object):

    def __init__(self, user, pkey, hosts, concurrency=10):
        self._ssh_user = user
        self._ssh_key = pkey
        self._hosts = hosts

        if not hosts:
            raise Exception('Need an non-empty list of hosts to talk to.')

        self._pool = eventlet.GreenPool(concurrency)
        self._hosts_client = {}
        self._init_clients()
        self._results = {}

    def _init_clients(self):
        for host in self._hosts:
            client = ParamikoSSHClient(host, username=self._ssh_user,
                                       key=self._ssh_key)
            try:
                client.connect()
            except Exception as e:
                print(str(e))
                print('Failed connecting to host %s.' % host)
            else:
                self._hosts_client[host] = client

    def run(self, cmd):
        count = 0
        results = {}

        while count <= len(self._hosts_client):
            for host in self._hosts_client.keys():
                while not self._pool.free():
                        eventlet.sleep(1)
                self._pool.spawn(self._run_command, cmd, host)
                count += 1

        self._pool.waitall()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(self._results)

    def _run_command(self, cmd, host):
        try:
            result = self._hosts_client[host].run(cmd)
            self._results[host] = result
        except:
            print('Failed executing command %s on host %s' % (cmd, host))


def main(user, pkey, hosts_str):
    hosts = hosts_str.split(",")
    client = ParallelSSHClient(user, pkey, hosts)
    client.run("pwd")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parallel SSH tester.')
    parser.add_argument('--hosts', required=True,
                        help='List of hosts to connect to')
    parser.add_argument('--private-key', required=True,
                        help='Private key to use.')
    parser.add_argument('--user', required=True,
                        help='SSH user name.')
    args = parser.parse_args()

    main(user=args.user, pkey=args.private_key, hosts_str=args.hosts)
