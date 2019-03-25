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

from st2common import log as logging


__all__ = [
    'get_available_backends',
    'get_backend_instance'
]

LOG = logging.getLogger(__name__)

BACKENDS_NAMESPACE = 'st2common.rbac.backend'


def get_available_backends():
    """
    Return names of the available / installed backends.

    :rtype: ``list`` of ``str``
    """
    from stevedore.extension import ExtensionManager

    manager = ExtensionManager(namespace=BACKENDS_NAMESPACE, invoke_on_load=False)
    return manager.names()


def get_backend_instance(name):
    """
    Retrieve a class instance for the provided backend.

    :param name: Backend name.
    :type name: ``str``
    """
    from stevedore.driver import DriverManager

    LOG.debug('Retrieving backend instance for backend "%s"' % (name))

    try:
        manager = DriverManager(namespace=BACKENDS_NAMESPACE, name=name,
                                invoke_on_load=False)
    except RuntimeError:
        message = 'Invalid RBAC backend specified: %s' % (name)
        LOG.exception(message)
        raise ValueError(message)

    cls = manager.driver
    cls_instance = cls()

    return cls_instance
