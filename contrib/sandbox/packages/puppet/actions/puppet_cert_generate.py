#!/usr/bin/env python

import argparse

from lib.actions import PuppetBaseAction

__all__ = [
    'PuppetCertGenerateAction'
]


class PuppetCertGenerateAction(PuppetBaseAction):
    def run(self, host):
        args = ['cert', 'generate', host]

        cmd = self._get_full_command(args=args)
        self._run_command(cmd=cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate a certificate for a named client')
    parser.add_argument('--host', help='Hostname of a client to generate the certificate for',
                        required=True)
    args = vars(parser.parse_args())

    action = PuppetCertGenerateAction()
    action.run(**args)
