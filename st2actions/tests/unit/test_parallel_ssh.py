# Licensed to the Apache Software Foundation (ASF) under one or more
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
import os

from mock import (patch, Mock, MagicMock)
import unittest2

from st2actions.runners.ssh.parallel_ssh import ParallelSSHClient
from st2actions.runners.ssh.paramiko_ssh import ParamikoSSHClient
from st2actions.runners.ssh.paramiko_ssh import SSHCommandTimeoutError
import st2tests.config as tests_config
tests_config.parse_args()


class ParallelSSHTests(unittest2.TestCase):

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_connect_with_password(self):
        hosts = ['localhost', '127.0.0.1']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   password='ubuntu',
                                   connect=False)
        client.connect()
        expected_conn = {
            'allow_agent': False,
            'look_for_keys': False,
            'password': 'ubuntu',
            'username': 'ubuntu',
            'timeout': 60,
            'port': 22
        }
        for host in hosts:
            expected_conn['hostname'] = host
            client._hosts_client[host].client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_connect_with_random_ports(self):
        hosts = ['localhost:22', '127.0.0.1:55', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   password='ubuntu',
                                   connect=False)
        client.connect()
        expected_conn = {
            'allow_agent': False,
            'look_for_keys': False,
            'password': 'ubuntu',
            'username': 'ubuntu',
            'timeout': 60,
            'port': 22
        }
        for host in hosts:
            hostname, port = client._get_host_port_info(host)
            expected_conn['hostname'] = hostname
            expected_conn['port'] = port
            client._hosts_client[hostname].client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_connect_with_key(self):
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=False)
        client.connect()
        expected_conn = {
            'allow_agent': False,
            'look_for_keys': False,
            'key_filename': '~/.ssh/id_rsa',
            'username': 'ubuntu',
            'timeout': 60,
            'port': 22
        }
        for host in hosts:
            hostname, port = client._get_host_port_info(host)
            expected_conn['hostname'] = hostname
            expected_conn['port'] = port
            client._hosts_client[hostname].client.connect.assert_called_once_with(**expected_conn)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_connect_with_bastion(self):
        hosts = ['localhost', '127.0.0.1']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   bastion_host='testing_bastion_host',
                                   connect=False)
        client.connect()

        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            self.assertEqual(client._hosts_client[hostname].bastion_host, 'testing_bastion_host')

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, 'run', MagicMock(return_value=('/home/ubuntu', '', 0)))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_run_command(self):
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        client.run('pwd', timeout=60)
        expected_kwargs = {
            'timeout': 60
        }
        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            client._hosts_client[hostname].run.assert_called_with('pwd', **expected_kwargs)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_run_command_timeout(self):
        # Make sure stdout and stderr is included on timeout
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        mock_run = Mock(side_effect=SSHCommandTimeoutError(cmd='pwd', timeout=10,
                                                           stdout='a',
                                                           stderr='b'))
        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            host_client = client._hosts_client[host]
            host_client.run = mock_run

        results = client.run('pwd')
        for host in hosts:
            result = results[host]
            self.assertEqual(result['failed'], True)
            self.assertEqual(result['stdout'], 'a')
            self.assertEqual(result['stderr'], 'b')
            self.assertEqual(result['return_code'], -9)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, 'put', MagicMock(return_value={}))
    @patch.object(os.path, 'exists', MagicMock(return_value=True))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_put(self):
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        client.put('/local/stuff', '/remote/stuff', mode=0744)
        expected_kwargs = {
            'mode': 0744,
            'mirror_local_mode': False
        }
        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            client._hosts_client[hostname].put.assert_called_with('/local/stuff', '/remote/stuff',
                                                                  **expected_kwargs)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, 'delete_file', MagicMock(return_value={}))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_delete_file(self):
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        client.delete_file('/remote/stuff')
        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            client._hosts_client[hostname].delete_file.assert_called_with('/remote/stuff')

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, 'delete_dir', MagicMock(return_value={}))
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_delete_dir(self):
        hosts = ['localhost', '127.0.0.1', 'st2build001']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        client.delete_dir('/remote/stuff/', force=True)
        expected_kwargs = {
            'force': True,
            'timeout': None
        }
        for host in hosts:
            hostname, _ = client._get_host_port_info(host)
            client._hosts_client[hostname].delete_dir.assert_called_with('/remote/stuff/',
                                                                         **expected_kwargs)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_host_port_info(self):
        client = ParallelSSHClient(hosts=['dummy'],
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        # No port case. Port should be 22.
        host_str = '1.2.3.4'
        host, port = client._get_host_port_info(host_str)
        self.assertEqual(host, host_str)
        self.assertEqual(port, 22)

        # IPv6 with square brackets with port specified.
        host_str = '[fec2::10]:55'
        host, port = client._get_host_port_info(host_str)
        self.assertEqual(host, 'fec2::10')
        self.assertEqual(port, 55)

    @patch('paramiko.SSHClient', Mock)
    @patch.object(ParamikoSSHClient, 'run', MagicMock(
        return_value=(json.dumps({'foo': 'bar'}), '', 0))
    )
    @patch.object(ParamikoSSHClient, '_is_key_file_needs_passphrase',
                  MagicMock(return_value=False))
    def test_run_command_json_output_transformed_to_object(self):
        hosts = ['127.0.0.1']
        client = ParallelSSHClient(hosts=hosts,
                                   user='ubuntu',
                                   pkey_file='~/.ssh/id_rsa',
                                   connect=True)
        results = client.run('stuff', timeout=60)
        self.assertTrue('127.0.0.1' in results)
        self.assertDictEqual(results['127.0.0.1']['stdout'], {'foo': 'bar'})
