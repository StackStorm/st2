import paramiko

from paramiko_ssh import ParamikoSSHClient

__all__ = [
    'ParamikoSSHBastionClient'
]


class ParamikoSSHBastionClient(ParamikoSSHClient):
    """
    ParamikoSSHBastionClient utilizes a bastion host for bouncing the SSH connection.
    Outside of the connect and close methods the underlying behaviour of ParamikoSSHClient
    is not modified or overridden.
    """
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
        self.bastion_port = bastion_port if bastion_port else self.port
        self.bastion_username = bastion_username if bastion_username else self.username
        self.bastion_password = bastion_password if bastion_password else self.password
        self.bastion_key = bastion_key if bastion_key else self.key
        self.bastion_key_files = bastion_key_files if bastion_key_files else self.key_files
        self.bastion_key_material = bastion_key_material if bastion_key_material else self.key_material
        self.bastion_client = paramiko.SSHClient()
        self.bastion_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(self):
        """
        Connect to the remote node over SSH.

        :return: True if the connection has been successfully established,
                 False otherwise.
        :rtype: ``bool``
        """
        bastion_conninfo = {'hostname': self.bastion_hostname,
                            'port': self.bastion_port,
                            'username': self.bastion_username,
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

        bastion_extra = {'_hostname': self.bastion_hostname,
                         '_port': self.bastion_port,
                         '_username': self.bastion_username,
                         '_timeout': self.timeout}

        self.logger.debug('Connecting to bastion host', extra=bastion_extra)

        self.bastion_client.connect(**bastion_conninfo)

        transport = self.bastion_client.get_transport()
        real_addr = (self.hostname, self.port)
        # no attempt is made to bind local_addr, so something very "wrong" is used
        local_addr = ('256.256.256.256', 65536)
        channel = transport.open_channel("direct-tcpip", real_addr, local_addr)

        conninfo = {'hostname': '256.256.256.256',
                    'port': 65536,
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

        return True
