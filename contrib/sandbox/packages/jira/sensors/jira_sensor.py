# See ./requirements.txt for requirements.
import os
import time

from jira.client import JIRA


class JIRASensor(object):
    '''
    Sensor will monitor for any new projects created in JIRA and
    emit trigger instance when one is created.
    '''
    def __init__(self, container_service, config=None):
        self._container_service = container_service
        self._config = config
        self._jira_url = None
        # The Consumer Key created while setting up the "Incoming Authentication" in
        # JIRA for the Application Link.
        self._consumer_key = u''
        self._rsa_key = None
        self._jira_client = None
        self._access_token = u''
        self._access_secret = u''
        self._projects_available = None
        self._poll_interval = 30
        self._project = None
        self._issues_in_project = None
        self._jql_query = None

    def _read_cert(self, file_path):
        with open(file_path) as f:
            return f.read()

    def setup(self):
        self._jira_url = self._config['url']
        rsa_cert_file = self._config['rsa_cert_file']
        if not os.path.exists(rsa_cert_file):
            raise Exception('Cert file for JIRA OAuth not found at %s.' % rsa_cert_file)
        self._rsa_key = self._read_cert(rsa_cert_file)
        self._poll_interval = self._config.get('poll_interval', self._poll_interval)
        oauth_creds = {
            'access_token': self._config['oauth_token'],
            'access_token_secret': self._config['oauth_secret'],
            'consumer_key': self._config['consumer_key'],
            'key_cert': self._rsa_key
        }

        self._jira_client = JIRA(options={'server': self._jira_url},
                                 oauth=oauth_creds)
        if self._projects_available is None:
            self._projects_available = set()
            for proj in self._jira_client.projects():
                self._projects_available.add(proj.key)
        self._project = self._config.get('project', None)
        if not self._project or self._project not in self._projects_available:
            raise Exception('Invalid project (%s) to track.' % self._project)
        self._jql_query = 'project=%s' % self._project
        all_issues = self._jira_client.search_issues(self._jql_query, maxResults=None)
        self._issues_in_project = {issue.key: issue for issue in all_issues}
        self._dispatch_issues_trigger(self._issues_in_project['STORM-1'])

    def start(self):
        while True:
            self._detect_new_issues()
            time.sleep(self._poll_interval)

    def stop(self):
        pass

    def get_trigger_types(self):
        return [
            {
                'name': 'st2.jira.issue_tracker',
                'description': 'JIRA issues tracker',
                'payload_info': ['project', 'issue_name', 'issue_url', 'created', 'assignee',
                                 'fix_versions', 'issue_type']
            }
        ]

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _detect_new_issues(self):
        loop = True
        while loop:
            new_issues = self._jira_client.search_issues(self._jql_query, maxResults=50,
                                                         startAt=0)
            for issue in new_issues:
                if issue.key not in self._issues_in_project:
                    self._dispatch_issues_trigger(issue)
                    self._issues_in_project[issue.key] = issue
                else:
                    loop = False  # Hit a task already in issues known. Stop getting issues.
                    break

    def _dispatch_issues_trigger(self, issue):
        trigger = {}
        trigger['name'] = 'st2.jira.project_tracker'
        payload = {}
        payload['issue_name'] = issue.key
        payload['issue_url'] = issue.self
        payload['issue_browse_url'] = self._jira_url + '/browse/' + issue.key
        payload['project'] = self._project
        payload['created'] = issue.raw['fields']['created']
        payload['assignee'] = issue.raw['fields']['assignee']
        payload['fix_versions'] = issue.raw['fields']['fixVersions']
        payload['issue_type'] = issue.raw['fields']['issuetype']['name']
        self._container_service.dispatch(trigger, payload)
