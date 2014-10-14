#!/usr/bin/env python

import sys
import pipes
import argparse
import subprocess

__all__ = [
    'PuppetApplyAction'
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


class PuppetApplyAction(PuppetBaseAction):
    def run(self, file, execute=False, catalog=None, debug=False):
        args = ['apply']

        if execute:
            args += ['--execute']

        if catalog:
            args += ['--catalog=%s' % (catalog)]

        args += [file]

        cmd = self._get_full_command(args=args)
        self._run_command(cmd=cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply a standalone puppet manifest to a local system')
    parser.add_argument('--file', help='Path to the puppet module file',
                        required=True)
    parser.add_argument('--execute', help='Execute a specific piece of Puppet code',
                        action='store_true', required=False)
    parser.add_argument('--catalog', help='Specific JSON catalog file to use',
                        required=False)
    args = vars(parser.parse_args())

    action = PuppetApplyAction()
    action.run(**args)
