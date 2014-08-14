import os
import time

from jira.client import JIRA

RSA_CERT_FILE = '/home/vagrant/jira.pem'


class JIRASensor(object):
    '''
    Sensor will monitor for any new projects created in JIRA and
    emit trigger instance when one is created.
    '''
    def __init__(self, container_service):
        self._container_service = container_service
        self._jira_server = 'https://stackstorm.atlassian.net'
        # The Consumer Key created while setting up the "Incoming Authentication" in
        # JIRA for the Application Link.
        self._consumer_key = u''
        self._rsa_key = None
        self._jira_client = None
        self._access_token = u''
        self._access_secret = u''
        self._projects_available = None
        self._sleep_time = 30

    def _read_cert(self, file_path):
        with open(file_path) as f:
            return f.read()

    def setup(self):
        global RSA_CERT_FILE
        if not os.path.exists(RSA_CERT_FILE):
            raise Exception('Cert file for JIRA OAuth not found at %s.' % RSA_CERT_FILE)

        # The contents of the rsa.pem file generated (the private RSA key)
        self._rsa_key = self._read_cert(RSA_CERT_FILE)
        oauth_creds = {
            'access_token': self._access_token,
            'access_token_secret': self._access_secret,
            'consumer_key': self._consumer_key,
            'key_cert': self._rsa_key
        }

        self._jira_client = JIRA(options={'server': self._jira_server},
                                 oauth=oauth_creds)
        if self._projects_available is None:
            self._projects_available = set()
            for proj in self._jira_client.projects():
                self._projects_available.add(proj.key)

    def start(self):
        while True:
            for proj in self._jira_client.projects():
                if proj.key not in self._projects_available:
                    self._dispatch_trigger(proj)
                    self._projects_available.add(proj)
            time.sleep(self._sleep_time)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {
                'name': 'st2.jira.project_tracker',
                'description': 'Stackstorm JIRA projects tracker',
                'payload_info': ['project_name', 'project_url']
            }
        ]

    def _dispatch_trigger(self, proj):
        trigger = {}
        trigger['name'] = 'st2.jira.projects-tracker'
        payload = {}
        payload['project_name'] = proj.key
        payload['project_url'] = proj.self
        trigger['payload'] = payload
        self._container_service.dispatch(trigger)
