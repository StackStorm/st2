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

import eventlet

from st2common.ssh.paramiko_ssh import ParamikoSSHClient
from st2common import log as logging

LOG = logging.getLogger(__name__)


class ParallelSSHClient(object):

    def __init__(self, user, pkey, hosts, port=22, concurrency=10,
                 raise_on_error=False, connect=True):
        self._ssh_user = user
        self._ssh_key = pkey
        self._hosts = hosts
        self._ssh_port = port

        if not hosts:
            raise Exception('Need an non-empty list of hosts to talk to.')

        self._pool = eventlet.GreenPool(concurrency)
        self._hosts_client = {}
        self._bad_hosts = []
        self._scan_interval = 0.1
        if connect:
            self.connect(raise_on_error=raise_on_error)

    def connect(self, raise_on_error=False):
        for host in self._hosts:
            client = ParamikoSSHClient(host, username=self._ssh_user,
                                       key=self._ssh_key, port=self._ssh_port)
            try:
                client.connect()
            except:
                LOG.exception('Failed connecting to host: %s')
                if raise_on_error:
                    raise
                self._bad_hosts.append(host)
            else:
                self._hosts_client[host] = client

    def run(self, cmd, timeout=None):
        results = {}

        for host in self._hosts_client.keys():
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(self._run_command, cmd=cmd, host=host,
                             results=results, timeout=None)

        self._pool.waitall()
        return results

    def put(self, path, contents=None, chmod=None, mode='w'):
        results = {}

        for host in self._hosts_client.keys():
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(self._put_files, path=path, host=host,
                             contents=contents, chmod=chmod, mode=mode,
                             results=results)
        self._pool.waitall()
        return results

    def _run_command(self, host, cmd, results, timeout=None):
        try:
            result = self._hosts_client[host].run(cmd, timeout=timeout)
            results[host] = result
        except:
            LOG.exception('Failed executing command %s on host %s', cmd, host)

    def delete(self, path):
        results = {}

        for host in self._hosts_client.keys():
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(self._delete_files, host=host, path=path, results=results)

        self._pool.waitall()
        return results

    def close(self):
        for host in self._hosts_client.keys():
            try:
                self._hosts_client[host].close()
            except:
                LOG.exception('Failed shutting down SSH connection to host: %s', host)

    def _put_files(self, host, path, results, contents=None, chmod=None, mode='w'):
        try:
            result = self._hosts_client[host].put(path, contents=contents, chmod=chmod,
                                                  mode=mode)
            results[host] = result
        except:
            LOG.exception('Failed sending file(s) in path %s to host %s', path, host)

    def _delete_files(self, host, path, results):
        try:
            result = self._hosts_client[host].delete(host, path)
            results[host] = result
        except:
            LOG.exception('Failed deleting file(s) in path %s on host %s.', path, host)
