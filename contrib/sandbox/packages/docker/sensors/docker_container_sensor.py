#!/usr/bin/env python

# Requirements
# pip install docker-py

try:
    import simplejson as json
except ImportError:
    import json
import os
import time

import docker
import six


class DockerSensor(object):
    def __init__(self, container_service, config=None):
        self._running_containers = {}
        self._container_service = container_service
        self._config = config
        self._ps_opts = None
        self._poll_interval = 5  # seconds.

    def setup(self):
        docker_opts = self._config

        # Assign sane defaults.
        if docker_opts['version'] is None:
            docker_opts['version'] = '1.13'
        if docker_opts['url'] is None:
            docker_opts['url'] = 'unix://var/run/docker.sock'

        self._version = docker_opts['version']
        self._url = docker_opts['url']
        self._timeout = 10
        if docker_opts['timeout'] is not None:
            self._timeout = docker_opts['timeout']
        self._ps_opts = docker_opts['ps_options']
        self._client = docker.Client(base_url=self._url,
                                     version=self._version,
                                     timeout=self._timeout)
        self._running_containers = self._get_active_containers()
        self._poll_interval = docker_opts.get('poll_interval', self._poll_interval)

    def start(self):
        while True:
            containers = self._get_active_containers()

            # Deleted.
            for id, running_container in six.iteritems(self._running_containers):
                if id not in containers:
                    self._dispatch_trigger(running_container)

            # Added.
            for id, container in six.iteritems(containers):
                if id not in self._running_containers:
                    self._dispatch_trigger(container)

            self._running_containers = containers
            time.sleep(self._poll_interval)

    def stop(self):
        if getattr(self._client, 'close') is not None:
            self._client.close()

    def get_trigger_types(self):
        return [{
            'name': 'st2.docker.container_tracker',
            'description': 'Stackstorm Docker containers tracker',
            'payload_schema': {
                'type': 'object',
                'properties': {
                    'container_info': {
                        'type': 'object'
                    }
                }
            }
        }]

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass

    def _dispatch_trigger(self, container):
        trigger = {}
        trigger['name'] = 'st2.docker.container_tracker'
        payload = {}
        payload['container_info'] = container
        self._container_service.dispatch(trigger, payload)

    def _get_active_containers(self):
        opts = self._ps_opts
        containers = self._client.containers(quiet=opts['quiet'], all=opts['all'],
                                             trunc=opts['trunc'], latest=opts['latest'],
                                             since=opts['since'], before=opts['before'],
                                             limit=opts['limit'])
        return self._to_dict(containers)

    def _to_dict(self, containers):
        container_tuples = [(container['Id'], container) for container in containers]
        return dict(container_tuples)
