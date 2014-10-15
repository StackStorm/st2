from st2actions.runners.pythonrunner import Action

from lib.puppet_client import PuppetHTTPAPIClient


class PuppetBasePythonAction(Action):
    def __init__(self):
        super(PupperBasePythonAction, self).__init__()
        self.client = self._get_client()

    def _get_client(self):
        master_config = self.config['master']
        auth_config = self.config['auth']

        client = PuppetHTTPAPIClient(master_hostname=master_config['hostname'],
                                     master_port=master_config['port'],
                                     client_cert_path=auth_config['client_cert_path'],
                                     client_cert_key_path=auth_config['client_cert_key_path'],
                                     ca_cert_path=auth_config['ca_cert_path'])

        return client
