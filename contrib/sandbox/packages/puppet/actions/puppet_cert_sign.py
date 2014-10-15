from lib.python_actions import PuppetBasePythonAction

__all__ = [
    'PuppetCertSignAction'
]


class PuppetCertSignAction(PuppetBasePythonAction):
    def run(self, environment, host):
        success = self.client.cert_sign(environment=environment, host=host)
