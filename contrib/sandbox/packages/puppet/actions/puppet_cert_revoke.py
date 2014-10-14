#!/usr/bin/env python

import sys
import pipes
import argparse
import subprocess

__all__ = [
    'PuppetCertRevokeAction'
]


class PuppetBaseAction(object):
    PUPPET_BINARY = 'puppet'

    def _run_command(self, cmd):
        cmd_string = ' '.join(pipes.quote(s) for s in cmd)
        sys.stderr.write('Running command "%s"\n' % (cmd_string))
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        exit_code = process.returncode

        return self._handle_command_result(exit_code=exit_code, stdout=stdout,
                                           stderr=stderr)

    def _get_full_command(self, args):
        cmd = [self.PUPPET_BINARY] + args
        return cmd

    def _handle_command_result(self, exit_code, stdout, stderr):
        if exit_code == 0:
            sys.stderr.write('Command successfully finished\n')
        else:
            error = []

            if stdout:
                error.append(stdout)

            if stderr:
                error.append(stderr)

            error = '\n'.join(error)
            sys.stderr.write('Command exited with an error: %s\n' % (error))
        sys.exit(exit_code)


class PuppetCertRevokeAction(PuppetBaseAction):
    def run(self, cert_sn_or_host):
        args = ['cert', 'revoke', cert_sn_or_host]

        cmd = self._get_full_command(args=args)
        self._run_command(cmd=cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Revoke the certificate of a client')
    parser.add_argument('--cert_sn_or_host', help='Serial number of a host of certificate to revoke',
                        required=True)
    args = vars(parser.parse_args())

    action = PuppetCertRevokeAction()
    action.run(**args)
