#!/usr/bin/env python

import argparse

from lib.remote_actions import PuppetBaseAction

__all__ = [
    'PuppetApplyAction'
]


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
