#!/usr/bin/env python

# Requirements
# pip install jira

import os
import sys
from jira.client import JIRA

RSA_CERT_FILE = '/home/vagrant/jira.pem'


class AuthedJiraClient(object):
    def __init__(self, jira_server, oauth_creds):
        self._client = JIRA(options={'server': jira_server},
                            oauth=oauth_creds)

    def is_project_exists(self, project):
        projs = self._client.projects()
        project_names = [proj.key for proj in projs]
        if project not in project_names:
            return False
        return True

    def create_issue(self, project=None, summary=None, desc=None, issuetype=None):
        issue_dict = {
            'project': {'key': project},
            'summary': summary,
            'description': desc,
            'issuetype': {'name': issuetype},
        }
        new_issue = self._client.create_issue(fields=issue_dict)
        return new_issue


def _read_cert(file_path):
    with open(file_path) as f:
        return f.read()


def _parse_args(args):
    params = {}
    params['jira_server'] = args[1]
    params['oauth_token'] = args[2]
    params['oauth_secret'] = args[3]
    params['consumer_key'] = args[4]
    params['project_name'] = args[5]
    params['issue_summary'] = args[6]
    params['issue_description'] = args[7]
    params['issue_type'] = args[8]
    return params


def _get_jira_client(params):
    if not os.path.exists(RSA_CERT_FILE):
        raise Exception('Cert file for JIRA OAuth not found at %s.' % RSA_CERT_FILE)
    rsa_key = _read_cert(RSA_CERT_FILE)
    oauth_creds = {
        'access_token': params['oauth_token'],
        'access_token_secret': params['oauth_secret'],
        'consumer_key': params['consumer_key'],
        'key_cert': rsa_key
    }
    jira_client = AuthedJiraClient(params['jira_server'], oauth_creds)
    return jira_client


def main(args):
    params = _parse_args(args)
    client = _get_jira_client(params)
    proj = params['project_name']

    try:
        if not client.is_project_exists(proj):
            raise Exception('Project ' + proj + ' does not exist.')
        issue = client.create_issue(project=params['project_name'],
                                    summary=params['issue_summary'],
                                    desc=params['issue_description'],
                                    issuetype=params['issue_type'])
    except Exception as e:
        sys.stderr.write(e.message + '\n')
    else:
        sys.stdout.write('Issue ' + issue + ' created.\n')

if __name__ == '__main__':
    main(sys.argv)
