#!/usr/bin/env python

# Requirements
# pip install gitpython
# Also requires git CLI tool to be installed.

import datetime
try:
    import simplejson as json
except ImportError:
    import json
import os
import time

from git.repo import Repo


class GitCommitSensor(object):
    def __init__(self, container_service, config=None):
        self._container_service = container_service
        self._config = config
        self._poll_interval = 1  # seconds.
        self._logger = self._container_service.get_logger(__name__)
        self._old_head = None
        self._remote = None

    def setup(self):
        git_opts = self._config

        if git_opts['url'] is None:
            raise Exception('Remote git URL not set.')

        self._url = git_opts['url']
        default_clone_dir = os.path.join(os.path.dirname(__file__), 'clones')
        self._local_path = git_opts.get('local_clone_path', default_clone_dir)
        self._poll_interval = git_opts.get('poll_interval', self._poll_interval)

        if os.path.exists(self._local_path):
            self._repo = Repo.init(self._local_path)
        else:
            try:
                self._repo = Repo.clone_from(self._url, self._local_path)
            except Exception:
                self._logger.exception('Unable to clone remote repo from %s',
                                       self._url)
                raise

        self._remote = self._repo.remote('origin')

    def start(self):
        while True:
            head = self._repo.commit()
            head_sha = head.hexsha

            if not self._old_head:
                self._old_head = head_sha
                if len(self._repo.heads) == 1:  # There is exactly one commit. Kick off a trigger.
                    self._dispatch_trigger(head)
                continue

            if head_sha != self._old_head:
                try:
                    self._dispatch_trigger(head)
                except Exception:
                    self._logger.exception('Failed dispatching trigger.')
                else:
                    self._old_head = head_sha

            time.sleep(self._poll_interval)
            try:
                pulled = self._remote.pull()
                self._logger.debug('Pulled info from remote repo. %s', pulled[0].commit)
            except:
                self._logger.exception('Failed git pull from remote repo.')

    def stop(self):
        pass

    def get_trigger_types(self):
        return [{
            'name': 'st2.git.head_sha_monitor',
            'description': 'Stackstorm git commits tracker',
            'payload_schema': {
                'type': 'object',
                'properties': {
                    'author': {'type': 'string'},
                    'author_email': {'type', 'string'},
                    'authored_date': {'type': 'string'},
                    'author_tz_offset': {'type': 'string'},
                    'committer': {'type': 'string'},
                    'committer_email': {'type': 'string'},
                    'committed_date': {'type': 'string'},
                    'committer_tz_offset': {'type': 'string'},
                    'revision': {'type': 'string'},
                    'branch': {'type': 'string'}
                }
            }
        }]

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _dispatch_trigger(self, commit):
        trigger = {}
        trigger['name'] = 'st2.git.head_sha_monitor'
        payload = {}
        payload['branch'] = self._repo.active_branch.name
        payload['revision'] = str(commit)
        payload['author'] = commit.author.name
        payload['author_email'] = commit.author.email
        payload['authored_date'] = self._to_date(commit.authored_date)
        payload['author_tz_offset'] = commit.author_tz_offset
        payload['committer'] = commit.committer.name
        payload['committer_email'] = commit.committer.email
        payload['committed_date'] = self._to_date(commit.committed_date)
        payload['committer_tz_offset'] = commit.committer_tz_offset
        self._logger.debug('Found new commit. Dispatching trigger: %s', payload)
        self._container_service.dispatch(trigger, payload)

    def _to_date(self, ts_epoch):
        return datetime.datetime.fromtimestamp(ts_epoch).strftime('%Y-%m-%dT%H:%M:%SZ')
