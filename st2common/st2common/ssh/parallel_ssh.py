# Licensed to the StackStorm, Inc ('StackStorm') under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import traceback

import eventlet

from st2common import log as logging
from st2common.ssh.paramiko_ssh import ParamikoSSHClient
import st2common.util.jsonify as jsonify

LOG = logging.getLogger(__name__)


class ParallelSSHClient(object):
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']
    CONNECT_ERROR = 'Cannot connect to host.'

    def __init__(self, hosts, user=None, password=None, pkey=None, port=22, concurrency=10,
                 raise_on_error=False, connect=True):
        self._ssh_user = user
        self._ssh_key = pkey
        self._ssh_password = password
        self._hosts = hosts
        self._ssh_port = port

        if not hosts:
            raise Exception('Need an non-empty list of hosts to talk to.')

        self._pool = eventlet.GreenPool(concurrency)
        self._hosts_client = {}
        self._bad_hosts = {}
        self._scan_interval = 0.1
        if connect:
            connect_results = self.connect(raise_on_error=raise_on_error)
            extra = {'_connect_results': connect_results}
            LOG.info('Connect to hosts complete.', extra=extra)

    def connect(self, raise_on_error=False):
        results = {}

        for host in self._hosts:
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(self._connect, host=host, results=results,
                             raise_on_error=raise_on_error)

        self._pool.waitall()
        return results

    def run(self, cmd, timeout=None, cwd=None):
        # Note that doing a chdir using sftp client in ssh_client doesn't really
        # set the session working directory. So we have to do this hack.
        if cwd:
            cmd = 'cd %s && %s' % (cwd, cmd)

        options = {
            'cmd': cmd,
            'timeout': timeout
        }
        results = self._execute_in_pool(self._run_command, **options)
        return jsonify.json_loads(results, ParallelSSHClient.KEYS_TO_TRANSFORM)

    def put(self, local_path, remote_path, mode=None, mirror_local_mode=False):

        if not os.path.exists(local_path):
            raise Exception('Local path %s does not exist.' % local_path)

        options = {
            'local_path': local_path,
            'remote_path': remote_path,
            'mode': mode,
            'mirror_local_mode': mirror_local_mode
        }

        return self._execute_in_pool(self._put_files, **options)

    def mkdir(self, path):
        options = {
            'path': path
        }
        return self._execute_in_pool(self._mkdir, **options)

    def delete_file(self, path):
        options = {
            'path': path
        }
        return self._execute_in_pool(self._delete_file, **options)

    def delete_dir(self, path, force=False, timeout=None):
        options = {
            'path': path,
            'force': force
        }
        return self._execute_in_pool(self._delete_dir, **options)

    def close(self):
        for host in self._hosts_client.keys():
            try:
                self._hosts_client[host].close()
            except:
                LOG.exception('Failed shutting down SSH connection to host: %s', host)

    def _execute_in_pool(self, execute_method, **kwargs):
        results = {}

        for host in self._bad_hosts.keys():
            results[host] = self._bad_hosts[host]

        for host in self._hosts_client.keys():
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(execute_method, host=host, results=results, **kwargs)

        self._pool.waitall()
        return results

    def _connect(self, host, results, raise_on_error=False):
        (hostname, port) = self._get_host_port_info(host)

        if not self._ssh_password:
            LOG.info('Connecting to host: %s port: %s as user: %s key: %s', hostname, port,
                     self._ssh_user, self._ssh_key)
        else:
            LOG.info('Connecting to host: %s port: %s as user: %s password: %s', hostname,
                     port, self._ssh_user, "<redacted>")

        client = ParamikoSSHClient(hostname, username=self._ssh_user,
                                   password=self._ssh_password,
                                   key=self._ssh_key, port=port)
        try:
            client.connect()
        except:
            error = 'Failed connecting to host %s.' % hostname
            LOG.exception(error)
            _, ex, tb = sys.exc_info()
            if raise_on_error:
                raise
            error = ' '.join([self.CONNECT_ERROR, str(ex)])
            error_dict = self._generate_error_result(error, tb)
            self._bad_hosts[hostname] = error_dict
            results[hostname] = error_dict
        else:
            self._hosts_client[hostname] = client
            results[hostname] = {'message': 'Connected to host.'}

    def _run_command(self, host, cmd, results, timeout=None):
        try:
            LOG.debug('Running command: %s on host: %s.', cmd, host)
            client = self._hosts_client[host]
            (stdout, stderr, exit_code) = client.run(cmd, timeout=timeout)
            is_succeeded = (exit_code == 0)
            results[host] = {'stdout': stdout, 'stderr': stderr, 'return_code': exit_code,
                             'succeeded': is_succeeded, 'failed': not is_succeeded}
        except:
            error = 'Failed executing command %s on host %s', cmd, host
            LOG.exception(error)
            _, _, tb = sys.exc_info()
            results[host] = self._generate_error_result(error, tb)

    def _put_files(self, local_path, remote_path, host, results, mode=None,
                   mirror_local_mode=False):
        try:
            LOG.debug('Copying file to host: %s' % host)
            if os.path.isdir(local_path):
                result = self._hosts_client[host].put_dir(local_path, remote_path)
            else:
                result = self._hosts_client[host].put(local_path, remote_path,
                                                      mirror_local_mode=mirror_local_mode,
                                                      mode=mode)
            LOG.debug('Result of copy: %s' % result)
            results[host] = result
        except:
            error = 'Failed sending file(s) in path %s to host %s' % (local_path, host)
            LOG.exception(error)
            _, _, tb = sys.exc_info()
            results[host] = self._generate_error_result(error, tb)

    def _mkdir(self, host, path, results):
        try:
            result = self._hosts_client[host].mkdir(path)
            results[host] = result
        except:
            error = 'Failed "mkdir %s" on host %s.' % (path, host)
            LOG.exception(error)
            _, _, tb = sys.exc_info()
            results[host] = self._generate_error_result(error, tb)

    def _delete_file(self, host, path, results):
        try:
            result = self._hosts_client[host].delete_file(path)
            results[host] = result
        except:
            error = 'Failed deleting file %s on host %s.' % (path, host)
            LOG.exception(error)
            _, _, tb = sys.exc_info()
            results[host] = self._generate_error_result(error, tb)

    def _delete_dir(self, host, path, results, force=False, timeout=None):
        try:
            result = self._hosts_client[host].delete_dir(path, force=force, timeout=timeout)
            results[host] = result
        except:
            error = 'Failed deleting dir %s on host %s.' % (path, host)
            LOG.exception(error)
            _, _, tb = sys.exc_info()
            results[host] = self._generate_error_result(error, tb)

    def _get_host_port_info(self, host_str):
        hostname = host_str
        port = self._ssh_port
        if ':' in hostname:
            hostname, port = host_str.split(':', 1)

        try:
            port = int(port)
        except:
            raise Exception('Invalid port %s specified.' % port)
        return (hostname, port)

    @staticmethod
    def _generate_error_result(error_msg, tb):
        error_dict = {
            'error': error_msg,
            'traceback': ''.join(traceback.format_tb(tb, 20)) if tb else '',
            'failed': True,
            'succeeded': False,
            'return_code': 255
        }
        return error_dict
