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

"""
Module containing utility functions for loading adapter / driver class instances for drivers using
stevedore dynamic plugin loading.
"""

from st2common import log as logging


__all__ = [
    'get_available_backends',
    'get_backend_driver',
    'get_backend_instance'
]

LOG = logging.getLogger(__name__)

BACKENDS_NAMESPACE = 'st2common.rbac.backend'


def get_available_backends(namespace, invoke_on_load=False):
    """
    Return names of the available / installed backends.

    :rtype: ``list`` of ``str``
    """
    # NOTE: We use lazy import because importing from stevedore adds significat import time
    # overhead to other modules which don't need this package (stevedore needs to inspect various
    # entrypoint files on disk for all the installed Python packages which is slow)
    from stevedore.extension import ExtensionManager

    manager = ExtensionManager(namespace=namespace, invoke_on_load=invoke_on_load)
    return manager.names()


def get_backend_driver(namespace, name, invoke_on_load=False):
    """
    Retrieve a driver (module / class / function) the provided backend.

    :param name: Backend name.
    :type name: ``str``
    """
    # NOTE: We use lazy import because importing from stevedore adds significat import time
    # overhead to other modules which don't need this package (stevedore needs to inspect various
    # entrypoint files on disk for all the installed Python packages which is slow)
    from stevedore.driver import DriverManager

    LOG.debug('Retrieving driver for backend "%s"' % (name))

    try:
        manager = DriverManager(namespace=namespace, name=name,
                                invoke_on_load=invoke_on_load)
    except RuntimeError:
        message = 'Invalid "%s" backend specified: %s' % (namespace, name)
        LOG.exception(message)
        raise ValueError(message)

    return manager.driver


def get_backend_instance(namespace, name, invoke_on_load=False):
    """
    Retrieve a class instance for the provided backend.

    :param name: Backend name.
    :type name: ``str``
    """
    cls = get_backend_driver(namespace=namespace, name=name, invoke_on_load=invoke_on_load)
    cls_instance = cls()

    return cls_instance
