#!/usr/bin/env python

import argparse

from lib.actions import PuppetBaseAction

__all__ = [
    'PuppetCertSignAction'
]


class PuppetCertSignAction(PuppetBaseAction):
    def run(self, host, all=False):
        args = ['cert', 'sign']

        if all:
            args += ['--all']

        args += [host]

        cmd = self._get_full_command(args=args)
        self._run_command(cmd=cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Sign an outstanding certificate request')
    parser.add_argument('--host', help='Hostname to use',
                        required=True)
    parser.add_argument('--all', help='Operate on all the items',
                        action='store_true', required=False)
    args = vars(parser.parse_args())

    action = PuppetCertSignAction()
    action.run(**args)
