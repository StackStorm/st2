# Requirements
# pip install jira

try:
    import simplejson as json
except ImportError:
    import json
import os
import time

from jira.client import JIRA

CONFIG_FILE = './jira_config.json'


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
        self._poll_interval = 30
        self._config = None

    def _read_cert(self, file_path):
        with open(file_path) as f:
            return f.read()

    def _parse_config(self):
        global CONFIG_FILE
        if not os.path.exists(CONFIG_FILE):
            raise Exception('Config file %s not found.' % CONFIG_FILE)
        with open(CONFIG_FILE) as f:
            self._config = json.load(f)
        rsa_cert_file = self._config['rsa_cert_file']
        if not os.path.exists(rsa_cert_file):
            raise Exception('Cert file for JIRA OAuth not found at %s.' % rsa_cert_file)
        self._rsa_key = self._read_cert(rsa_cert_file)

    def setup(self):
        self._parse_config()
        self._poll_interval = self._config.get('poll_interval', self._poll_interval)
        oauth_creds = {
            'access_token': self._config['oauth_token'],
            'access_token_secret': self._config['oauth_secret'],
            'consumer_key': self._config['consumer_key'],
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
                    self._projects_available.add(proj.key)
            time.sleep(self._poll_interval)

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

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _dispatch_trigger(self, proj):
        trigger = {}
        trigger['name'] = 'st2.jira.project_tracker'
        payload = {}
        payload['project_name'] = proj.key
        payload['project_url'] = proj.self
        self._container_service.dispatch(trigger, payload)
