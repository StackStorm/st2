#!/usr/bin/env python

# Requirements
# pip install jira

try:
    import simplejson as json
except ImportError:
    import json
import os
import sys

from jira.client import JIRA

CONFIG_FILE = './jira_config.json'


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
    params['project_name'] = args[1]
    params['issue_summary'] = args[2]
    params['issue_description'] = args[3]
    params['issue_type'] = args[4]
    return params


def _get_jira_client(config):
    rsa_cert_file = config['rsa_cert_file']
    if not os.path.exists(rsa_cert_file):
        raise Exception('Cert file for JIRA OAuth not found at %s.' % rsa_cert_file)
    rsa_key = _read_cert(rsa_cert_file)
    oauth_creds = {
        'access_token': config['oauth_token'],
        'access_token_secret': config['oauth_secret'],
        'consumer_key': config['consumer_key'],
        'key_cert': rsa_key
    }
    jira_client = AuthedJiraClient(config['jira_server'], oauth_creds)
    return jira_client


def _get_config():
    global CONFIG_FILE
    if not os.path.exists(CONFIG_FILE):
        raise Exception('Config file not found at %s.' % CONFIG_FILE)
    with open(CONFIG_FILE) as f:
        return json.load(f)


def main(args):
    try:
        client = _get_jira_client(_get_config())
    except Exception as e:
        sys.stderr.write('Failed to create JIRA client: %s\n' % str(e))
        sys.exit(1)

    params = _parse_args(args)
    proj = params['project_name']
    try:
        if not client.is_project_exists(proj):
            raise Exception('Project ' + proj + ' does not exist.')
        issue = client.create_issue(project=params['project_name'],
                                    summary=params['issue_summary'],
                                    desc=params['issue_description'],
                                    issuetype=params['issue_type'])
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.exit(2)
    else:
        sys.stdout.write('Issue ' + issue + ' created.\n')

if __name__ == '__main__':
    main(sys.argv)
