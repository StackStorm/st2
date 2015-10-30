import paramiko

from paramiko_ssh import ParamikoSSHClient


class ParamikoSSHBastionClient(ParamikoSSHClient):
    def __init__(self,
                 hostname, bastion_hostname, port=22, username=None,
                 password=None, key=None, key_files=None,
                 key_material=None, timeout=None,
                 bastion_port=22, bastion_username=None,
                 bastion_password=None, bastion_key=None,
                 bastion_key_files=None, bastion_key_material=None):
        super(ParamikoSSHBastionClient, self). \
            __init__(hostname, port, username, password, key, key_files,
                     key_material, timeout)
        if bastion_key_files and bastion_key_material:
            raise ValueError('key_files and key_material arguments are mutually exclusive')
        self.bastion_hostname = bastion_hostname
        self.bastion_port = bastion_port if bastion_port else port
        self.bastion_username = bastion_username if bastion_username else username
        self.bastion_password = bastion_password if bastion_password else password
        self.bastion_key = bastion_key if bastion_key else key
        self.bastion_key_files = bastion_key_files if bastion_key_files else key_files
        self.bastion_key_material = bastion_key_material if bastion_key_material else key_material
        self.bastion_client = paramiko.SSHClient()
        self.bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.bastion_sftp = None

    def connect(self):
        """
        Connect to the remote node over SSH.

        :return: True if the connection has been successfully established,
                 False otherwise.
        :rtype: ``bool``
        """
        bastion_conninfo = {'hostname': self.hostname,
                            'port': self.port,
                            'username': self.username,
                            'allow_agent': False,
                            'look_for_keys': False,
                            'timeout': self.timeout}

        if self.bastion_password:
            bastion_conninfo['password'] = self.bastion_password

        if self.bastion_key_files:
            bastion_conninfo['key_filename'] = self.bastion_key_files

        if self.bastion_key_material:
            bastion_conninfo['pkey'] = self._get_pkey_object(key_material=self.bastion_key_material)

        if not self.bastion_password and not (self.bastion_key_files or self.bastion_key_material):
            bastion_conninfo['allow_agent'] = True
            bastion_conninfo['look_for_keys'] = True

        bastion_extra = {'_hostname': self.hostname,
                         '_port': self.port,
                         '_username': self.username,
                         '_timeout': self.timeout}

        self.logger.debug('Connecting to server', extra=bastion_extra)

        self.bastion_client.connect(**bastion_conninfo)
        self.bastion_sftp = self.client.open_sftp()

        transport = self.bastion_client.get_transport()
        real_addr = (self.hostname, self.port)
        local_addr = ('127.0.0.1', 1234)  # as far as I can tell paramiko doesn't actually bind 1234
        channel = transport.open_channel("direct-tcpip", real_addr, local_addr)

        conninfo = {'hostname': '127.0.0.1',
                    'port': 1234,
                    'sock': channel,
                    'username': self.username,
                    'allow_agent': False,
                    'look_for_keys': False,
                    'timeout': self.timeout}

        if self.password:
            conninfo['password'] = self.password

        if self.key_files:
            conninfo['key_filename'] = self.key_files

        if self.key_material:
            conninfo['pkey'] = self._get_pkey_object(key_material=self.key_material)

        if not self.password and not (self.key_files or self.key_material):
            conninfo['allow_agent'] = True
            conninfo['look_for_keys'] = True

        extra = {'_hostname': self.hostname, '_port': self.port,
                 '_username': self.username, '_timeout': self.timeout}
        self.logger.debug('Connecting to server', extra=extra)

        self.client.connect(**conninfo)
        self.sftp = self.client.open_sftp()
        return True

    def close(self):
        super(ParamikoSSHBastionClient, self).close()

        self.bastion_client.close()
        if self.bastion_sftp:
            self.bastion_sftp.close()

        return True
