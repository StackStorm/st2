from lib.python_actions import PuppetBasePythonAction

__all__ = [
    'PuppetCertCleanAction'
]


class PuppetCertCleanAction(PuppetBasePythonAction):
    def run(self, environment, host):
        success = self.client.cert_clean(environment=environment, host=host)
