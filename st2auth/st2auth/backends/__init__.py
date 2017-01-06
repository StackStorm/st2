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

import traceback
import json

from oslo_config import cfg
from stevedore.driver import DriverManager
from stevedore.extension import ExtensionManager

from st2common import log as logging

__all__ = [
    'get_available_backends',
    'get_backend_instance'
]

LOG = logging.getLogger(__name__)

BACKENDS_NAMESPACE = 'st2auth.backends.backend'


def get_available_backends():
    """
    Return names of the available / installed authentication backends.

    :rtype: ``list`` of ``str``
    """
    manager = ExtensionManager(namespace=BACKENDS_NAMESPACE, invoke_on_load=False)
    return manager.names()


def get_backend_instance(name):
    """
    Retrieve a class instance for the provided auth backend.

    :param name: Backend name.
    :type name: ``str``
    """

    LOG.debug('Retrieving backend instance for backend "%s"' % (name))

    try:
        manager = DriverManager(namespace=BACKENDS_NAMESPACE, name=name,
                                invoke_on_load=False)
    except RuntimeError:
        message = 'Invalid authentication backend specified: %s' % (name)
        LOG.exception(message)
        raise ValueError(message)

    backend_kwargs = cfg.CONF.auth.backend_kwargs

    if backend_kwargs:
        try:
            kwargs = json.loads(backend_kwargs)
        except ValueError as e:
            raise ValueError('Failed to JSON parse backend settings for backend "%s": %s' %
                             (name, str(e)))
    else:
        kwargs = {}

    cls = manager.driver

    try:
        cls_instance = cls(**kwargs)
    except Exception as e:
        tb_msg = traceback.format_exc()
        class_name = cls.__name__
        msg = ('Failed to instantiate auth backend "%s" (class %s) with backend settings '
               '"%s": %s' % (name, class_name, str(kwargs), str(e)))
        msg += '\n\n' + tb_msg
        exc_cls = type(e)
        raise exc_cls(msg)

    return cls_instance
