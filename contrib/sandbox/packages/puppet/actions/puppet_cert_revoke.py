#!/usr/bin/env python

import argparse

from lib.actions import PuppetBaseAction

__all__ = [
    'PuppetCertRevokeAction'
]


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
