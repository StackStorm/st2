#!/usr/bin/env python

import sys
import pipes
import argparse
import subprocess

__all__ = [
    'PuppetRunAgentAction'
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


class PuppetRunAgentAction(PuppetBaseAction):
    def run(self, server=None, certname=None, daemonize=False, onetime=True,
            debug=None):
        args = ['agent']

        if server:
            args += ['--server=%s' % (server)]

        if certname:
            args += ['--certname=%s' % (server)]

        if daemonize:
            args += ['--daemonize']
        else:
            args += ['--no-daemonize']

        if onetime:
            args += ['--onetime']

        if debug:
            args += ['--debug']

        cmd = self._get_full_command(args=args)
        self._run_command(cmd=cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run puppet agent')
    parser.add_argument('--server', help='Name of the puppet master server',
                        required=False)
    parser.add_argument('--certname', help='Certname (unique ID) of the client',
                        required=False)
    parser.add_argument('--daemonize', help='Send the process into the background',
                        action='store_true', default=False, required=False)
    parser.add_argument('--no_onetime', help='Disable one time run mode',
                        action='store_true', required=False)
    parser.add_argument('--debug', help='Enable full debugging',
                        action='store_true', default=False, required=False)
    args = vars(parser.parse_args())

    no_onetime = args.pop('no_onetime', False)
    args['onetime'] = not no_onetime

    if not args['daemonize'] and not args['onetime']:
        raise ValueError('When --no_onetime is provided, --daemonize needs'
                         ' to be provided as well')

    action = PuppetRunAgentAction()
    action.run(**args)
