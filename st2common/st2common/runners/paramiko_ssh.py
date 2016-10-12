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

import os
import posixpath
from StringIO import StringIO
import time

import eventlet
from oslo_config import cfg

import paramiko

# Depending on your version of Paramiko, it may cause a deprecation
# warning on Python 2.6.
# Ref: https://bugs.launchpad.net/paramiko/+bug/392973

from st2common.log import logging
from st2common.util.misc import strip_shell_chars
from st2common.util.shell import quote_unix
from st2common.constants.runners import REMOTE_RUNNER_PRIVATE_KEY_HEADER

__all__ = [
    'ParamikoSSHClient',

    'SSHCommandTimeoutError'
]


class SSHCommandTimeoutError(Exception):
    """
    Exception which is raised when an SSH command times out.
    """

    def __init__(self, cmd, timeout, stdout=None, stderr=None):
        """
        :param stdout: Stdout which was consumed until the timeout occured.
        :type stdout: ``str``

        :param stdout: Stderr which was consumed until the timeout occured.
        :type stderr: ``str``
        """
        self.cmd = cmd
        self.timeout = timeout
        self.stdout = stdout
        self.stderr = stderr
        message = 'Command didn\'t finish in %s seconds' % (timeout)
        super(SSHCommandTimeoutError, self).__init__(message)

    def __repr__(self):
        return ('<SSHCommandTimeoutError: cmd="%s",timeout=%s)>' %
                (self.cmd, self.timeout))

    def __str__(self):
        return self.message


class ParamikoSSHClient(object):
    """
    A SSH Client powered by Paramiko.
    """

    # Maximum number of bytes to read at once from a socket
    CHUNK_SIZE = 1024

    # How long to sleep while waiting for command to finish
    SLEEP_DELAY = 1.5

    # Connect socket timeout
    CONNECT_TIMEOUT = 60

    def __init__(self, hostname, port=22, username=None, password=None, bastion_host=None,
                 key_files=None, key_material=None, timeout=None, passphrase=None):
        """
        Authentication is always attempted in the following order:

        - The key passed in (if key is provided)
        - Any key we can find through an SSH agent (only if no password and
          key is provided)
        - Any "id_rsa" or "id_dsa" key discoverable in ~/.ssh/ (only if no
          password and key is provided)
        - Plain username/password auth, if a password was given (if password is
          provided)
        """
        if key_files and key_material:
            raise ValueError(('key_files and key_material arguments are '
                              'mutually exclusive'))

        if passphrase and not (key_files or key_material):
            raise ValueError('passphrase should accompany private key material')

        credentials_provided = password or key_files or key_material
        if not credentials_provided and cfg.CONF.system_user.ssh_key_file:
            key_files = cfg.CONF.system_user.ssh_key_file

        self.hostname = hostname
        self.port = port
        self.username = username if username else cfg.CONF.system_user
        self.password = password
        self.key_files = key_files
        self.timeout = timeout or ParamikoSSHClient.CONNECT_TIMEOUT
        self.key_material = key_material
        self.bastion_host = bastion_host
        self.passphrase = passphrase

        self.logger = logging.getLogger(__name__)

        self.client = None
        self.sftp_client = None

        self.bastion_client = None
        self.bastion_socket = None

    def connect(self):
        """
        Connect to the remote node over SSH.

        :return: True if the connection has been successfully established,
                 False otherwise.
        :rtype: ``bool``
        """
        if self.bastion_host:
            self.logger.debug('Bastion host specified, connecting')
            self.bastion_client = self._connect(host=self.bastion_host)
            transport = self.bastion_client.get_transport()
            real_addr = (self.hostname, self.port)
            # fabric uses ('', 0) for direct-tcpip, this duplicates that behaviour
            # see https://github.com/fabric/fabric/commit/c2a9bbfd50f560df6c6f9675603fb405c4071cad
            local_addr = ('', 0)
            self.bastion_socket = transport.open_channel('direct-tcpip', real_addr, local_addr)

        self.client = self._connect(host=self.hostname, socket=self.bastion_socket)
        return True

    def put(self, local_path, remote_path, mode=None, mirror_local_mode=False):
        """
        Upload a file to the remote node.

        :type local_path: ``st``
        :param local_path: File path on the local node.

        :type remote_path: ``str``
        :param remote_path: File path on the remote node.

        :type mode: ``int``
        :param mode: Permissions mode for the file. E.g. 0744.

        :type mirror_local_mode: ``int``
        :param mirror_local_mode: Should remote file mirror local mode.

        :return: Attributes of the remote file.
        :rtype: :class:`posix.stat_result` or ``None``
        """

        if not local_path or not remote_path:
            raise Exception('Need both local_path and remote_path. local: %s, remote: %s' %
                            local_path, remote_path)
        local_path = quote_unix(local_path)
        remote_path = quote_unix(remote_path)

        extra = {'_local_path': local_path, '_remote_path': remote_path, '_mode': mode,
                 '_mirror_local_mode': mirror_local_mode}
        self.logger.debug('Uploading file', extra=extra)

        if not os.path.exists(local_path):
            raise Exception('Path %s does not exist locally.' % local_path)

        rattrs = self.sftp.put(local_path, remote_path)

        if mode or mirror_local_mode:
            local_mode = mode
            if not mode or mirror_local_mode:
                local_mode = os.stat(local_path).st_mode

            # Cast to octal integer in case of string
            if isinstance(local_mode, basestring):
                local_mode = int(local_mode, 8)
            local_mode = local_mode & 07777
            remote_mode = rattrs.st_mode
            # Only bitshift if we actually got an remote_mode
            if remote_mode is not None:
                remote_mode = (remote_mode & 07777)
            if local_mode != remote_mode:
                self.sftp.chmod(remote_path, local_mode)

        return rattrs

    def put_dir(self, local_path, remote_path, mode=None, mirror_local_mode=False):
        """
        Upload a dir to the remote node.

        :type local_path: ``str``
        :param local_path: Dir path on the local node.

        :type remote_path: ``str``
        :param remote_path: Base dir path on the remote node.

        :type mode: ``int``
        :param mode: Permissions mode for the file. E.g. 0744.

        :type mirror_local_mode: ``int``
        :param mirror_local_mode: Should remote file mirror local mode.

        :return: List of files created on remote node.
        :rtype: ``list`` of ``str``
        """

        extra = {'_local_path': local_path, '_remote_path': remote_path, '_mode': mode,
                 '_mirror_local_mode': mirror_local_mode}
        self.logger.debug('Uploading dir', extra=extra)

        if os.path.basename(local_path):
            strip = os.path.dirname(local_path)
        else:
            strip = os.path.dirname(os.path.dirname(local_path))

        remote_paths = []

        for context, dirs, files in os.walk(local_path):
            rcontext = context.replace(strip, '', 1)
            # normalize pathname separators with POSIX separator
            rcontext = rcontext.replace(os.sep, '/')
            rcontext = rcontext.lstrip('/')
            rcontext = posixpath.join(remote_path, rcontext)

            if not self.exists(rcontext):
                self.sftp.mkdir(rcontext)

            for d in dirs:
                n = posixpath.join(rcontext, d)
                if not self.exists(n):
                    self.sftp.mkdir(n)

            for f in files:
                local_path = os.path.join(context, f)
                n = posixpath.join(rcontext, f)
                # Note that quote_unix is done by put anyways.
                p = self.put(local_path=local_path, remote_path=n,
                             mirror_local_mode=mirror_local_mode, mode=mode)
                remote_paths.append(p)

        return remote_paths

    def exists(self, remote_path):
        """
        Validate whether a remote file or directory exists.

        :param remote_path: Path to remote file.
        :type remote_path: ``str``

        :rtype: ``bool``
        """
        try:
            self.sftp.lstat(remote_path).st_mode
        except IOError:
            return False

        return True

    def mkdir(self, dir_path):
        """
        Create a directory on remote box.

        :param dir_path: Path to remote directory to be created.
        :type dir_path: ``str``

        :return: Returns nothing if successful else raises IOError exception.

        :rtype: ``None``
        """

        dir_path = quote_unix(dir_path)
        extra = {'_dir_path': dir_path}
        self.logger.debug('mkdir', extra=extra)
        return self.sftp.mkdir(dir_path)

    def delete_file(self, path):
        """
        Delete a file on remote box.

        :param path: Path to remote file to be deleted.
        :type path: ``str``

        :return: True if the file has been successfully deleted, False
                 otherwise.
        :rtype: ``bool``
        """

        path = quote_unix(path)
        extra = {'_path': path}
        self.logger.debug('Deleting file', extra=extra)
        self.sftp.unlink(path)
        return True

    def delete_dir(self, path, force=False, timeout=None):
        """
        Delete a dir on remote box.

        :param path: Path to remote dir to be deleted.
        :type path: ``str``

        :param force: Optional Forcefully remove dir.
        :type force: ``bool``

        :param timeout: Optional Time to wait for dir to be deleted. Only relevant for force.
        :type timeout: ``int``

        :return: True if the file has been successfully deleted, False
                 otherwise.
        :rtype: ``bool``
        """

        path = quote_unix(path)
        extra = {'_path': path}
        if force:
            command = 'rm -rf %s' % path
            extra['_command'] = command
            extra['_force'] = force
            self.logger.debug('Deleting dir', extra=extra)
            return self.run(command, timeout=timeout)

        self.logger.debug('Deleting dir', extra=extra)
        return self.sftp.rmdir(path)

    def run(self, cmd, timeout=None, quote=False):
        """
        Note: This function is based on paramiko's exec_command()
        method.

        :param timeout: How long to wait (in seconds) for the command to
                        finish (optional).
        :type timeout: ``float``
        """

        if quote:
            cmd = quote_unix(cmd)

        extra = {'_cmd': cmd}
        self.logger.info('Executing command', extra=extra)

        # Use the system default buffer size
        bufsize = -1

        transport = self.client.get_transport()
        chan = transport.open_session()

        start_time = time.time()
        if cmd.startswith('sudo'):
            # Note that fabric does this as well. If you set pty, stdout and stderr
            # streams will be combined into one.
            chan.get_pty()
        chan.exec_command(cmd)

        stdout = StringIO()
        stderr = StringIO()

        # Create a stdin file and immediately close it to prevent any
        # interactive script from hanging the process.
        stdin = chan.makefile('wb', bufsize)
        stdin.close()

        # Receive all the output
        # Note #1: This is used instead of chan.makefile approach to prevent
        # buffering issues and hanging if the executed command produces a lot
        # of output.
        #
        # Note #2: If you are going to remove "ready" checks inside the loop
        # you are going to have a bad time. Trying to consume from a channel
        # which is not ready will block for indefinitely.
        exit_status_ready = chan.exit_status_ready()

        if exit_status_ready:
            stdout.write(self._consume_stdout(chan).getvalue())
            stderr.write(self._consume_stderr(chan).getvalue())

        while not exit_status_ready:
            current_time = time.time()
            elapsed_time = (current_time - start_time)

            if timeout and (elapsed_time > timeout):
                # TODO: Is this the right way to clean up?
                chan.close()

                stdout = strip_shell_chars(stdout.getvalue())
                stderr = strip_shell_chars(stderr.getvalue())
                raise SSHCommandTimeoutError(cmd=cmd, timeout=timeout, stdout=stdout,
                                             stderr=stderr)

            stdout.write(self._consume_stdout(chan).getvalue())
            stderr.write(self._consume_stderr(chan).getvalue())

            # We need to check the exist status here, because the command could
            # print some output and exit during this sleep bellow.
            exit_status_ready = chan.exit_status_ready()

            if exit_status_ready:
                break

            # Short sleep to prevent busy waiting
            eventlet.sleep(self.SLEEP_DELAY)
        # print('Wait over. Channel must be ready for host: %s' % self.hostname)

        # Receive the exit status code of the command we ran.
        status = chan.recv_exit_status()

        stdout = strip_shell_chars(stdout.getvalue())
        stderr = strip_shell_chars(stderr.getvalue())

        extra = {'_status': status, '_stdout': stdout, '_stderr': stderr}
        self.logger.debug('Command finished', extra=extra)

        return [stdout, stderr, status]

    def close(self):
        self.logger.debug('Closing server connection')

        self.client.close()

        if self.sftp_client:
            self.sftp_client.close()

        if self.bastion_client:
            self.bastion_client.close()

        return True

    @property
    def sftp(self):
        """
        Method which lazily establishes SFTP connection if one is not established yet when this
        variable is accessed.
        """
        if not self.sftp_client:
            self.sftp_client = self.client.open_sftp()

        return self.sftp_client

    def _consume_stdout(self, chan):
        """
        Try to consume stdout data from chan if it's receive ready.
        """

        out = bytearray()
        stdout = StringIO()
        if chan.recv_ready():
            data = chan.recv(self.CHUNK_SIZE)
            out += data

            while data:
                ready = chan.recv_ready()

                if not ready:
                    break

                data = chan.recv(self.CHUNK_SIZE)
                out += data

        stdout.write(self._get_decoded_data(out))
        return stdout

    def _consume_stderr(self, chan):
        """
        Try to consume stderr data from chan if it's receive ready.
        """

        out = bytearray()
        stderr = StringIO()
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(self.CHUNK_SIZE)
            out += data

            while data:
                ready = chan.recv_stderr_ready()

                if not ready:
                    break

                data = chan.recv_stderr(self.CHUNK_SIZE)
                out += data

        stderr.write(self._get_decoded_data(out))
        return stderr

    def _get_decoded_data(self, data):
        try:
            return data.decode('utf-8')
        except:
            self.logger.exception('Non UTF-8 character found in data: %s', data)
            raise

    def _get_pkey_object(self, key_material, passphrase):
        """
        Try to detect private key type and return paramiko.PKey object.
        """

        for cls in [paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey]:
            try:
                key = cls.from_private_key(StringIO(key_material), password=passphrase)
            except paramiko.ssh_exception.SSHException:
                # Invalid key, try other key type
                pass
            else:
                return key

        # If a user passes in something which looks like file path we throw a more friendly
        # exception letting the user know we expect the contents a not a path.
        # Note: We do it here and not up the stack to avoid false positives.
        contains_header = REMOTE_RUNNER_PRIVATE_KEY_HEADER in key_material.lower()
        if not contains_header and (key_material.count('/') >= 1 or key_material.count('\\') >= 1):
            msg = ('"private_key" parameter needs to contain private key data / content and not '
                   'a path')
        elif passphrase:
            msg = 'Invalid passphrase or invalid/unsupported key type'
        else:
            msg = 'Invalid or unsupported key type'

        raise paramiko.ssh_exception.SSHException(msg)

    def _connect(self, host, socket=None):
        """

        :type host: ``str``
        :param host: Host to connect to

        :type socket: :class:`paramiko.Channel` or an opened :class:`socket.socket`
        :param socket: If specified, won't open a socket for communication to the specified host
                       and will use this instead

        :return: A connected SSHClient
        :rtype: :class:`paramiko.SSHClient`
        """
        conninfo = {'hostname': host,
                    'port': self.port,
                    'username': self.username,
                    'allow_agent': False,
                    'look_for_keys': False,
                    'timeout': self.timeout}

        if self.password:
            conninfo['password'] = self.password

        if self.key_files:
            conninfo['key_filename'] = self.key_files

            passphrase_reqd = self._is_key_file_needs_passphrase(self.key_files)
            if passphrase_reqd and not self.passphrase:
                msg = ('Private key file %s is passphrase protected. Supply a passphrase.' %
                       self.key_files)
                raise paramiko.ssh_exception.PasswordRequiredException(msg)

            if self.passphrase:
                # Optional passphrase for unlocking the private key
                conninfo['password'] = self.passphrase

        if self.key_material:
            conninfo['pkey'] = self._get_pkey_object(key_material=self.key_material,
                                                     passphrase=self.passphrase)

        if not self.password and not (self.key_files or self.key_material):
            conninfo['allow_agent'] = True
            conninfo['look_for_keys'] = True

        extra = {'_hostname': host, '_port': self.port,
                 '_username': self.username, '_timeout': self.timeout}
        self.logger.debug('Connecting to server', extra=extra)

        if socket:
            conninfo['sock'] = socket

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(**conninfo)

        return client

    @staticmethod
    def _is_key_file_needs_passphrase(file):
        for cls in [paramiko.RSAKey, paramiko.DSSKey, paramiko.ECDSAKey]:
            try:
                cls.from_private_key_file(file, password=None)
            except paramiko.ssh_exception.PasswordRequiredException:
                return True
            except paramiko.ssh_exception.SSHException:
                continue

        return False

    def __repr__(self):
        return ('<ParamikoSSHClient hostname=%s,port=%s,username=%s,id=%s>' %
                (self.hostname, self.port, self.username, id(self)))
