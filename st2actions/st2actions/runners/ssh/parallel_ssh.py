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

import json
import re
import os
import traceback

import eventlet

from st2common.constants.secrets import MASKED_ATTRIBUTE_VALUE
from st2actions.runners.ssh.paramiko_ssh import ParamikoSSHClient
from st2actions.runners.ssh.paramiko_ssh import SSHCommandTimeoutError
from st2common import log as logging
from st2common.exceptions.ssh import NoHostsConnectedToException
import st2common.util.jsonify as jsonify
from st2common.util import ip_utils

LOG = logging.getLogger(__name__)


class ParallelSSHClient(object):
    KEYS_TO_TRANSFORM = ['stdout', 'stderr']
    CONNECT_ERROR = 'Cannot connect to host.'

    def __init__(self, hosts, user=None, password=None, pkey_file=None, pkey_material=None, port=22,
                 bastion_host=None, concurrency=10, raise_on_any_error=False, connect=True,
                 passphrase=None):
        self._ssh_user = user
        self._ssh_key_file = pkey_file
        self._ssh_key_material = pkey_material
        self._ssh_password = password
        self._hosts = hosts
        self._successful_connects = 0
        self._ssh_port = port
        self._bastion_host = bastion_host
        self._passphrase = passphrase

        if not hosts:
            raise Exception('Need an non-empty list of hosts to talk to.')

        self._pool = eventlet.GreenPool(concurrency)
        self._hosts_client = {}
        self._bad_hosts = {}
        self._scan_interval = 0.1

        if connect:
            connect_results = self.connect(raise_on_any_error=raise_on_any_error)
            extra = {'_connect_results': connect_results}
            LOG.debug('Connect to hosts complete.', extra=extra)

    def connect(self, raise_on_any_error=False):
        """
        Connect to hosts in hosts list. Returns status of connect as a dict.

        :param raise_on_any_error: Optional Raise an exception even if connecting to one
                                   of the hosts fails.
        :type raise_on_any_error: ``boolean``

        :rtype: ``dict`` of ``str`` to ``dict``
        """
        results = {}

        for host in self._hosts:
            while not self._pool.free():
                eventlet.sleep(self._scan_interval)
            self._pool.spawn(self._connect, host=host, results=results,
                             raise_on_any_error=raise_on_any_error)

        self._pool.waitall()

        if self._successful_connects < 1:
            # We definitely have to raise an exception in this case.
            LOG.error('Unable to connect to any of the hosts.',
                      extra={'connect_results': results})
            msg = ('Unable to connect to any one of the hosts: %s.\n\n connect_errors=%s' %
                   (self._hosts, json.dumps(results, indent=2)))
            raise NoHostsConnectedToException(msg)

        return results

    def run(self, cmd, timeout=None):
        """
        Run a command on remote hosts. Returns a dict containing results
        of execution from all hosts.

        :param cmd: Command to run. Must be shlex quoted.
        :type cmd: ``str``

        :param timeout: Optional Timeout for the command.
        :type timeout: ``int``

        :param cwd: Optional Current working directory. Must be shlex quoted.
        :type cwd: ``str``

        :rtype: ``dict`` of ``str`` to ``dict``
        """

        options = {
            'cmd': cmd,
            'timeout': timeout
        }
        results = self._execute_in_pool(self._run_command, **options)
        return results

    def put(self, local_path, remote_path, mode=None, mirror_local_mode=False):
        """
        Copy a file or folder to remote host.

        :param local_path: Path to local file or dir. Must be shlex quoted.
        :type local_path: ``str``

        :param remote_path: Path to remote file or dir. Must be shlex quoted.
        :type remote_path: ``str``

        :param mode: Optional mode to use for the file or dir.
        :type mode: ``int``

        :param mirror_local_mode: Optional Flag to mirror the mode
                                           on local file/dir on remote host.
        :type mirror_local_mode: ``boolean``

        :rtype: ``dict`` of ``str`` to ``dict``
        """

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
        """
        Create a directory on remote hosts.

        :param path: Path to remote dir that must be created. Must be shlex quoted.
        :type path: ``str``

        :rtype path: ``dict`` of ``str`` to ``dict``
        """

        options = {
            'path': path
        }
        return self._execute_in_pool(self._mkdir, **options)

    def delete_file(self, path):
        """
        Delete a file on remote hosts.

        :param path: Path to remote file that must be deleted. Must be shlex quoted.
        :type path: ``str``

        :rtype path: ``dict`` of ``str`` to ``dict``
        """

        options = {
            'path': path
        }
        return self._execute_in_pool(self._delete_file, **options)

    def delete_dir(self, path, force=False, timeout=None):
        """
        Delete a dir on remote hosts.

        :param path: Path to remote dir that must be deleted. Must be shlex quoted.
        :type path: ``str``

        :rtype path: ``dict`` of ``str`` to ``dict``
        """

        options = {
            'path': path,
            'force': force
        }
        return self._execute_in_pool(self._delete_dir, **options)

    def close(self):
        """
        Close all open SSH connections to hosts.
        """

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

    def _connect(self, host, results, raise_on_any_error=False):
        (hostname, port) = self._get_host_port_info(host)

        extra = {'host': host, 'port': port, 'user': self._ssh_user}
        if self._ssh_password:
            extra['password'] = '<redacted>'
        elif self._ssh_key_file:
            extra['key_file_path'] = self._ssh_key_file
        else:
            extra['private_key'] = '<redacted>'

        LOG.debug('Connecting to host.', extra=extra)

        client = ParamikoSSHClient(hostname, username=self._ssh_user,
                                   password=self._ssh_password,
                                   bastion_host=self._bastion_host,
                                   key_files=self._ssh_key_file,
                                   key_material=self._ssh_key_material,
                                   passphrase=self._passphrase,
                                   port=port)
        try:
            client.connect()
        except Exception as ex:
            error = 'Failed connecting to host %s.' % hostname
            LOG.exception(error)
            if raise_on_any_error:
                raise
            error_dict = self._generate_error_result(exc=ex, message=error)
            self._bad_hosts[hostname] = error_dict
            results[hostname] = error_dict
        else:
            self._successful_connects += 1
            self._hosts_client[hostname] = client
            results[hostname] = {'message': 'Connected to host.'}

    def _run_command(self, host, cmd, results, timeout=None):
        try:
            LOG.debug('Running command: %s on host: %s.', cmd, host)
            client = self._hosts_client[host]
            (stdout, stderr, exit_code) = client.run(cmd, timeout=timeout)
            is_succeeded = (exit_code == 0)
            result_dict = {'stdout': stdout, 'stderr': stderr, 'return_code': exit_code,
                           'succeeded': is_succeeded, 'failed': not is_succeeded}
            results[host] = jsonify.json_loads(result_dict, ParallelSSHClient.KEYS_TO_TRANSFORM)
        except Exception as ex:
            cmd = self._sanitize_command_string(cmd=cmd)
            error = 'Failed executing command "%s" on host "%s"' % (cmd, host)
            LOG.exception(error)
            results[host] = self._generate_error_result(exc=ex, message=error)

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
        except Exception as ex:
            error = 'Failed sending file(s) in path %s to host %s' % (local_path, host)
            LOG.exception(error)
            results[host] = self._generate_error_result(exc=ex, message=error)

    def _mkdir(self, host, path, results):
        try:
            result = self._hosts_client[host].mkdir(path)
            results[host] = result
        except Exception as ex:
            error = 'Failed "mkdir %s" on host %s.' % (path, host)
            LOG.exception(error)
            results[host] = self._generate_error_result(exc=ex, message=error)

    def _delete_file(self, host, path, results):
        try:
            result = self._hosts_client[host].delete_file(path)
            results[host] = result
        except Exception as ex:
            error = 'Failed deleting file %s on host %s.' % (path, host)
            LOG.exception(error)
            results[host] = self._generate_error_result(exc=ex, message=error)

    def _delete_dir(self, host, path, results, force=False, timeout=None):
        try:
            result = self._hosts_client[host].delete_dir(path, force=force, timeout=timeout)
            results[host] = result
        except Exception as ex:
            error = 'Failed deleting dir %s on host %s.' % (path, host)
            LOG.exception(error)
            results[host] = self._generate_error_result(exc=ex, message=error)

    def _get_host_port_info(self, host_str):
        (hostname, port) = ip_utils.split_host_port(host_str)
        if not port:
            port = self._ssh_port

        return (hostname, port)

    @staticmethod
    def _sanitize_command_string(cmd):
        """
        Remove any potentially sensitive information from the command string.

        For now we only mask the values of the sensitive environment variables.
        """
        if not cmd:
            return cmd

        result = re.sub('ST2_ACTION_AUTH_TOKEN=(.+?)\s+?', 'ST2_ACTION_AUTH_TOKEN=%s ' %
                        (MASKED_ATTRIBUTE_VALUE), cmd)
        return result

    @staticmethod
    def _generate_error_result(exc, message):
        """
        :param exc: Raised exception.
        :type exc: Exception.

        :param message: Error message which will be prefixed to the exception exception message.
        :type message: ``str``
        """
        exc_message = getattr(exc, 'message', str(exc))
        error_message = '%s: %s' % (message, exc_message)
        traceback_message = traceback.format_exc()

        if isinstance(exc, SSHCommandTimeoutError):
            return_code = -9
            timeout = True
        else:
            timeout = False
            return_code = 255

        stdout = getattr(exc, 'stdout', None) or ''
        stderr = getattr(exc, 'stderr', None) or ''

        error_dict = {
            'failed': True,
            'succeeded': False,
            'timeout': timeout,
            'return_code': return_code,
            'stdout': stdout,
            'stderr': stderr,
            'error': error_message,
            'traceback': traceback_message,
        }
        return error_dict

    def __repr__(self):
        return ('<ParallelSSHClient hosts=%s,user=%s,id=%s>' %
                (repr(self._hosts), self._ssh_user, id(self)))
