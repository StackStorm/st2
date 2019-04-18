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

from __future__ import absolute_import

from oslo_config import cfg

from st2common import log as logging

from st2common.util import driver_loader


__all__ = [
    'get_available_backends',
    'get_backend_instance',
    'get_rbac_backend'
]

LOG = logging.getLogger(__name__)

BACKENDS_NAMESPACE = 'st2common.rbac.backend'

# Cache which maps backed name -> backend class instance
# NOTE: We use cache to avoid slow stevedore dynamic filesystem instrospection on every
# get_rbac_backend function call
BACKENDS_CACHE = {}


def get_available_backends():
    return driver_loader.get_available_backends(namespace=BACKENDS_NAMESPACE)


def get_backend_instance(name, use_cache=True):
    if name not in BACKENDS_CACHE or not use_cache:
        rbac_backend = driver_loader.get_backend_instance(namespace=BACKENDS_NAMESPACE, name=name)
        BACKENDS_CACHE[name] = rbac_backend

    rbac_backend = BACKENDS_CACHE[name]
    return rbac_backend


def get_rbac_backend():
    """
    Return RBACBackend class instance.
    """
    rbac_backend = get_backend_instance(cfg.CONF.rbac.backend)
    return rbac_backend
