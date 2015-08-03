#!/usr/bin/env python2.7

import argparse
import os
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


def main(user, pkey, hosts_str, cmd, path):
    hosts = hosts_str.split(",")
    client = ParallelSSHClient(user, pkey, hosts)
    pp = pprint.PrettyPrinter(indent=4)

    if path:
        if not os.path.exists(path):
            raise Exception('File not found.')
        results = client.put(path, '/home/lakshmi/test')
        pp.pprint('Copy results: \n%s' % results)
        results = client.run('ls -rlth')
        pp.pprint('ls results: \n%s' % results)

    if cmd:
        results = client.run(cmd)
        pp.pprint('cmd results: \n%s' % results)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parallel SSH tester.')
    parser.add_argument('--hosts', required=True,
                        help='List of hosts to connect to')
    parser.add_argument('--private-key', required=True,
                        help='Private key to use.')
    parser.add_argument('--user', required=True,
                        help='SSH user name.')
    parser.add_argument('--cmd', required=False,
                        help='Command to run on host.')
    parser.add_argument('--path', required=False,
                        help='Path to copy to remote host.')
    args = parser.parse_args()

    main(user=args.user, pkey=args.private_key, hosts_str=args.hosts, cmd=args.cmd,
         path=args.path)
