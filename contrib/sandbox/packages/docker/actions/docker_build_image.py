#!/usr/bin/env python

# Requirements
# pip install docker

try:
    import simplejson as json
except ImportError:
    import json
import os
import sys

import docker
import six

CONFIG_FILE = './docker_config.json'


class DockerWrapper(object):
    def __init__(self, docker_opts):
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
        self._client = docker.Client(base_url=self._url,
                                     version=self._version,
                                     timeout=self._timeout)
        self._docker_build_opts = docker_opts['build_options']

    def build(self, path=None, fileobj=None, tag=None):
        if path is None and fileobj is None:
            raise Exception('Either dir containing dockerfile or path to dockerfile ' +
                            ' must be provided.')
        if path is not None and fileobj is not None:
            sys.stdout.write('Using path to dockerfile: %s\n' % fileobj)
        opts = self._docker_build_opts
        sys.stdout.write('Building docker container. Path = %s, Tag = %s\n' % (path, tag))
        # Depending on docker version, stream may or may not be forced. So let's just always
        # use streaming.
        result = self._client.build(path=path, fileobj=fileobj, tag=tag, quiet=opts['quiet'],
                                    nocache=opts['nocache'], rm=opts['rm'],
                                    stream=True, timeout=opts['timeout'])
        try:
            json_output = six.advance_iterator(result)
            while json_output:
                output = json.loads(json_output)
                sys.stdout.write(output['stream'] + '\n')
                json_output = six.advance_iterator(result)
        except:
            pass


def _get_config(file):
    if not os.path.exists(file):
        raise Exception('Config file not found at %s.' % file)
    with open(file) as f:
        return json.load(f)


def _parse_args(args):
    params = {}
    params['docker_artifacts_path'] = args[1]
    params['tag_for_image'] = args[2]
    return params


def main(args):
    config = _get_config(CONFIG_FILE)
    try:
        docker_client = DockerWrapper(config)
    except Exception as e:
        sys.stderr.write('Unable to create docker client: %s\n' % str(e))
        sys.exit(1)
    params = _parse_args(args)
    if os.path.isdir(params['docker_artifacts_path']):
        docker_client.build(path=params['docker_artifacts_path'], tag=params['tag_for_image'])
    else:
        docker_client.build(fileobj=params['docker_artifacts_path'], tag=params['tag_for_image'])

if __name__ == '__main__':
    main(sys.argv)
