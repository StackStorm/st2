#!/usr/bin/env python

import sys

from libcloud.compute.base import NodeSize
from libcloud.compute.base import NodeImage
from libcloud.compute.base import NodeLocation

from lib.actions import BaseAction

__all__ = [
    'CreateVMAction'
]


class CreateVMAction(BaseAction):
    description = 'Create a new VM'

    def run(self, credentials, name, size_id, image_id, location_id=None):
        driver = self._get_driver_for_credentials(credentials=credentials)
        size = NodeSize(id=size_id, name=None,
                        ram=None, disk=None, bandwidth=None,
                        price=None, driver=driver)
        image = NodeImage(id=image_id, name=None,
                          driver=driver)
        location = NodeLocation(id=location_id, name=None,
                                country=None, driver=driver)

        sys.stderr.write('Creating node...')

        kwargs = {'name': name, 'size': size, 'image': image}

        if location_id:
            kwargs['location'] = location

        node = driver.create_node(**kwargs)

        sys.stderr.write('Node successfully created: %s' % (node))
        return node
