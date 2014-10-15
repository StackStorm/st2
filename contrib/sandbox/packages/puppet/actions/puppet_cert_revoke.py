import argparse

from lib.python_actions import PuppetBasePythonAction

__all__ = [
    'PuppetCertRevokeAction'
]


class PuppetCertRevokeAction(PuppetBasePythonAction):
    def run(self, environment, host):
        success = self.client.cert_revoke(environment=environment, host=host)
