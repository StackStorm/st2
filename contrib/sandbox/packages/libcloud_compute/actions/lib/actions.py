import os
import sys
import json
import argparse

try:
    import libcloud
except ImportError:
    message = ('Missing "apache-libcloud", please install it using pip:\n'
               'pip install apache-libcloud')
    raise ImportError(message)

from libcloud.compute.providers import get_driver
from libcloud.compute.base import Node
from libcloud.compute.base import NodeSize
from libcloud.compute.base import NodeImage
from libcloud.compute.base import NodeLocation

__all__ = [
    'StartVMAction',
    'StopVMAction',
    'RebootVMAction',
    'DestroyVMAction',
    'CreateVMAction',
    'ImportPublicSSHKeyAction'
]

CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), 'config.json')


class BaseAction(object):
    description = None

    def __init__(self):
        self.config = self._parse_config()

    def get_parser(self):
        parser = argparse.ArgumentParser(description=self.description)
        parser.add_argument('--credentials', help='Name of the credentials (as defined in the config) to use',
                            required=True)

        return parser

    def get_arguments(self):
        parser = self.get_parser()
        args = parser.parse_args()
        return args

    def _parse_config(self):
        with open(CONFIG_FILE_PATH, 'r') as fp:
            content = fp.read()

        config = json.loads(content)
        return config

    def _get_driver_for_credentials(self, credentials):
        """
        Retrieve Libcloud provider driver instance for a particular credentials
        set defined in the config.

        :type credentials: ``str``
        """
        provider_config = self.config['credentials'].get(credentials, None)

        if not provider_config:
            raise ValueError(('Invalid credentials set name "%s". Please make'
                              ' sure that credentials set with this name is'
                              ' defined in the config' % (credentials)))

        cls = get_driver(provider_config['provider'])

        # TODO: If and when we switch to the Python runner, we can cache the
        # driver instance
        driver_args = [provider_config['api_key'],
                       provider_config['api_secret']]
        driver_kwargs = {}

        if 'region' in provider_config:
            driver_kwargs['region'] = provider_config['region']

        if 'extra_kwargs' in provider_config:
            assert isinstance(provider_config['extra_kwargs'], dict)
            driver_kwargs.update(provider_config['extra_kwargs'])

        driver = cls(*driver_args, **driver_kwargs)
        return driver

    def _get_driver_for_active_credentials(self):
        """
        Return Libcloud driver instance for the selected credentials set.
        """
        arguments = self.get_arguments()
        credentials = arguments.credentials
        driver = self._get_driver_for_credentials(credentials=credentials)
        return driver


class SingleVMAction(BaseAction):
    description = 'Libcloud VM action'

    def get_parser(self):
        parser = super(SingleVMAction, self).get_parser()
        parser.add_argument('--vm-id', help='ID of a VM to operate on',
                            required=True)

        return parser

    def _get_node_for_id(self, node_id, driver=None):
        """
        Retrieve Libcloud node instance for the provided node id.
        """
        node = Node(id=node_id, name=None, state=None, public_ips=None,
                    private_ips=None, driver=driver)
        return node


class StartVMAction(SingleVMAction):
    description = 'Start a VM'

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        node = self._get_node_for_id(node_id=arguments.vm_id, driver=driver)

        sys.stderr.write('Starting node: %s' % (node))
        status = driver.ex_stop_node(node=node)

        if status is True:
            sys.stderr.write('Successfully started node "%s"' % (node))
        else:
            sys.stderr.write('Failed to start node "%s"' % (node))

        return status


class StopVMAction(SingleVMAction):
    description = 'Stop a VM'

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        node = self._get_node_for_id(node_id=arguments.vm_id, driver=driver)

        sys.stderr.write('Stopping node: %s' % (node))
        status = driver.ex_stop_node(node=node)

        if status is True:
            sys.stderr.write('Successfully stopped node "%s"' % (node))
        else:
            sys.stderr.write('Failed to stop node "%s"' % (node))

        return status


class RebootVMAction(SingleVMAction):
    description = 'Reboot a VM'

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        node = self._get_node_for_id(node_id=arguments.vm_id, driver=driver)

        sys.stderr.write('Rebooting node: %s' % (node))
        status = driver.reboot_node(node=node)

        if status is True:
            sys.stderr.write('Successfully rebooted node "%s"' % (node))
        else:
            sys.stderr.write('Failed to reboot node "%s"' % (node))

        return status


class DestroyVMAction(SingleVMAction):
    description = 'Destroy a VM'

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        node = self._get_node_for_id(node_id=arguments.vm_id, driver=driver)

        sys.stderr.write('Destroy node: %s' % (node))
        status = driver.destroy_node(node=node)

        if status is True:
            sys.stderr.write('Successfully destroyed node "%s"' % (node))
        else:
            sys.stderr.write('Failed to destroy node "%s"' % (node))

        return status


class CreateVMAction(BaseAction):
    description = 'Create a new VM'

    # TODO
    # To make it more user-friendly and easier to work across different
    # providers we could maybe support partial / fuzzy matches for size
    # and image selection (e.g. find size closest to the desired one and
    # find image which matches a partial name)

    def get_parser(self):
        parser = super(CreateVMAction, self).get_parser()
        parser.add_argument('--name', help='Name of a new VM',
                            required=True)
        parser.add_argument('--size-id', help='ID of the size to use',
                            required=True)
        parser.add_argument('--image-id', help='ID of the image to use',
                            required=True)
        parser.add_argument('--location-id', help='ID of the location to use',
                            required=False)

        return parser

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        name = arguments.name
        size = NodeSize(id=arguments.size_id, name=None,
                        ram=None, disk=None, bandwidth=None,
                        price=None, driver=driver)
        image = NodeImage(id=arguments.image_id, name=None,
                          driver=driver)
        location = NodeLocation(id=arguments.location_id, name=None,
                                country=None, driver=driver)

        sys.stderr.write('Creating node...')

        kwargs = {'name': name, 'size': size, 'image': image}

        if arguments.location_id:
            kwargs['location'] = location

        node = driver.create_node(**kwargs)

        sys.stderr.write('Node successfully created: %s' % (node))
        return node


class ImportPublicSSHKeyAction(BaseAction):
    description = 'Import public SSH key'

    def get_parser(self):
        parser = super(ImportPublicSSHKeyAction, self).get_parser()
        parser.add_argument('--name', help='Name for the imported key pair',
                            required=True)
        parser.add_argument('--key-material', help='Public SSH key material',
                            required=True)

        return parser

    def run(self):
        arguments = self.get_arguments()

        driver = self._get_driver_for_active_credentials()
        return driver.import_key_pair_from_string(name=arguments.name,
                                                  key_material=arguments.key_material)
