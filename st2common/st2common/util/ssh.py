import os
import socket
import sys

import eventlet
import paramiko
from fabric.operations import _execute as fabric_execute_cmd_blocking

from st2common import log as logging
from st2common.exceptions.connection import AuthenticationException
from st2common.exceptions.connection import (ConnectionErrorException, UnknownHostException)

eventlet.monkey_patch(
    os=True,
    select=True,
    socket=True,
    thread=False if '--use-debugger' in sys.argv else True,
    time=True
)

LOG = logging.getLogger('st2.util.ssh.paramikoclient')
# This implementation of SSH is heavily inspired by parallel-ssh which uses gvent instead of
# eventlet.


class SSHClient(object):
    '''
        Thread unsafe version of SSHClient.
    '''
    def __init__(self, host,
                 user=None, password=None, port=None,
                 key=None, connect_max_retries=2):
        ssh_config = paramiko.SSHConfig()
        _ssh_config_file = os.path.sep.join([os.path.expanduser('~'),
                                             '.ssh',
                                             'config'])

        if os.path.exists(_ssh_config_file):
            ssh_config.parse(open(_ssh_config_file))
        host_config = ssh_config.lookup(host)
        resolved_address = (host_config['hostname'] if
                            'hostname' in host_config
                            else host)
        _user = host_config['user'] if 'user' in host_config else None
        if user:
            user = user
        else:
            user = _user
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())
        self.client = client
        self.channel = None
        self.user = user
        self.password = password
        self.key = key
        self.port = port if port else 22
        self.host = resolved_address
        self._max_retries = 2
        self._connect_to_host()
        self.running = False

    def _connect_to_host(self, retries=1):
        """Connect to host, throw UnknownHost exception on DNS errors"""
        try:
            self.client.connect(self.host, username=self.user,
                                password=self.password, port=self.port,
                                pkey=self.key)
        except socket.gaierror as e:
            LOG.error("Could not resolve host '%s'", self.host)
            self._retry(retries)
            raise UnknownHostException("%s - %s" % (str(e.args[1]),
                                                    self.host,))
        except socket.error as e:
            LOG.error("Error connecting to host '%s:%s'" % (self.host,
                                                            self.port,))
            self._retry(retries)
            raise ConnectionErrorException("%s for host '%s:%s'" % (str(e.args[1]),
                                                                    self.host,
                                                                    self.port,))
        except paramiko.AuthenticationException, e:
            raise AuthenticationException(e)

    def _retry(self, retries):
        while retries < self._max_retries:
            print('Retrying host ...')
            eventlet.sleep(5)
            return self._connect_to_host(retries=retries + 1)

    def execute_async(self, command, sudo=False, **kwargs):
        channel = self.client.get_transport().open_session()
        if sudo:
            channel.get_pty()
        (stdout, stderr) = (channel.makefile('rb'), channel.makefile_stderr('rb'))
        if sudo:
            command = 'sudo -S bash -c "%s"' % command.replace('"', '\\"')
        else:
            command = 'bash -c "%s"' % command.replace('"', '\\"')
        LOG.debug("Running command %s on %s", command, self.host)
        channel.exec_command(command, **kwargs)
        LOG.debug("Command finished executing")
        while not (channel.recv_ready() or channel.closed):
            eventlet.sleep(.2)
        return channel, self.host, stdout, stderr

    def execute_sync(self, command, sudo=False, timeout=4, **kwargs):
        '''
            Note this method performs a blocking SSH call. This means you have stdout and
            stderr as simple strings and you also have the exit code. Fabric _execute is
            designed as higher level API that abstracts away the notion of dealing with
            stdout and stderr as streams. If you want access to these streams directly
            and are willing to poll the channel for exit code, use execute_async instead.
        '''
        channel = self.client.get_transport().open_session()
        pty = False
        if sudo:
            pty = True  # Keep paramiko happy.
        return fabric_execute_cmd_blocking(channel, command, pty=pty, combine_stderr=False,
                                           timeout=timeout)

    def _make_sftp(self):
        transport = self.client.get_transport()
        transport.open_session()
        return paramiko.SFTPClient.from_transport(transport)

    def mkdir(self, sftp, directory):
        try:
            sftp.mkdir(directory)
        except IOError as error:
            LOG.error("Error occured creating directory on %s - %s", self.host, error)

    def copy_file(self, local_file, remote_file):
        sftp = self._make_sftp()
        destination = remote_file.split(os.path.sep)
        remote_file = os.path.sep.join(destination)
        destination = destination[:-1]
        for directory in destination:
            try:
                sftp.stat(directory)
            except IOError:
                self.mkdir(sftp, directory)
        try:
            sftp.put(local_file, remote_file)
        except Exception as error:
            LOG.error("Error occured copying file to host %s - %s", self.host, error)
        else:
            LOG.info("Copied local file %s to remote destination %s:%s", local_file, self.host,
                     remote_file)
