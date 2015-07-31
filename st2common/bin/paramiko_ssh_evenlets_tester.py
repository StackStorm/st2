#!/usr/bin/env python2.7

import argparse
import pprint
import sys

import eventlet

from st2common.ssh.parallel_ssh import ParallelSSHClient

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True)


def main(user, pkey, hosts_str, cmd):
    hosts = hosts_str.split(",")
    client = ParallelSSHClient(user, pkey, hosts)
    results = client.run(cmd)
    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parallel SSH tester.')
    parser.add_argument('--hosts', required=True,
                        help='List of hosts to connect to')
    parser.add_argument('--private-key', required=True,
                        help='Private key to use.')
    parser.add_argument('--user', required=True,
                        help='SSH user name.')
    parser.add_argument('--cmd', required=True,
                        help='Command to run on host.')
    args = parser.parse_args()

    main(user=args.user, pkey=args.private_key, hosts_str=args.hosts, cmd=args.cmd)
